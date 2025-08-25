import asyncio
import json
import re
import ssl
import time
import os
from datetime import datetime
import html
import aiohttp
import pycountry
import brotli
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PeerIdInvalidError, ChatWriteForbiddenError
from telethon.tl.types import ReplyInlineMarkup, KeyboardButtonRow, InputKeyboardButtonUserProfile, KeyboardButtonCopy
from telethon.tl.custom import Button
from telethon.utils import get_display_name
from utils import LOGGER, SERVICE_PATTERNS, COUNTRY_ALIASES, LOGIN_URL, SMS_LIST_URL, SMS_NUMBERS_URL, SMS_DETAILS_URL, SMS_HEADERS, OTP_HISTORY_FILE, SMS_CACHE_FILE
from config import EMAIL, PASSWORD, CHAT_IDS, OWNER_ID, UPDATE_CHANNEL_URL

ssl._create_default_https_context = ssl._create_unverified_context
file_lock = asyncio.Lock()

def get_flag_emoji(country_code):
    if not country_code or len(country_code) != 2:
        return "🌍"
    code_points = [ord(c.upper()) - ord('A') + 0x1F1E6 for c in country_code]
    return chr(code_points[0]) + chr(code_points[1])

def get_country_emoji(country_name):
    country_name = COUNTRY_ALIASES.get(country_name, country_name)
    countries = pycountry.countries.search_fuzzy(country_name)
    if countries:
        return get_flag_emoji(countries[0].alpha_2)
    return "🌍"

async def load_sms_cache():
    async with file_lock:
        if os.path.exists(SMS_CACHE_FILE):
            with open(SMS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

async def save_sms_cache(cache):
    async with file_lock:
        with open(SMS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4)

async def load_otp_history():
    async with file_lock:
        if os.path.exists(OTP_HISTORY_FILE):
            with open(OTP_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

async def save_otp_history(history):
    async with file_lock:
        with open(OTP_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)

async def check_and_save_otp(number, otp, message_id):
    history = await load_otp_history()
    current_time = datetime.now().isoformat()
    if number not in history:
        history[number] = [{"otp": otp, "message_id": message_id, "timestamp": current_time}]
        await save_otp_history(history)
        return True
    for entry in history[number]:
        if entry["otp"] == otp and entry["message_id"] != message_id:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if (datetime.now() - entry_time).total_seconds() < 60:
                return False
    history[number].append({"otp": otp, "message_id": message_id, "timestamp": current_time})
    await save_otp_history(history)
    return True

def format_otp_with_spaces(otp):
    return otp

async def get_csrf_token(session):
    try:
        async with session.get(LOGIN_URL, timeout=10) as response:
            response.raise_for_status()
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_token'})
            if csrf_input is None:
                return None
            csrf_token = csrf_input.get('value')
            if not csrf_token:
                return None
            return csrf_token
    except Exception as e:
        LOGGER.error(f"Error getting CSRF token: {e}")
        return None

async def login(session, attempt=1):
    if attempt > 3:
        return False
    try:
        csrf_token = await get_csrf_token(session)
        if not csrf_token:
            await asyncio.sleep(10)
            return await login(session, attempt + 1)
        login_data = {
            "_token": csrf_token,
            "email": EMAIL,
            "password": PASSWORD
        }
        async with session.post(LOGIN_URL, data=login_data, timeout=30) as login_response:
            login_response.raise_for_status()
            if "dashboard" in str(login_response.url) or login_response.status == 200:
                return True
            await asyncio.sleep(10)
            return await login(session, attempt + 1)
    except Exception as e:
        LOGGER.error(f"Login error: {e}")
        await asyncio.sleep(10)
        return await login(session, attempt + 1)

async def refresh_session(session, last_login_time):
    current_time = time.time()
    if current_time - last_login_time >= 1800:
        if await login(session):
            return True, current_time
        return False, last_login_time
    return True, last_login_time

async def fetch_sms(session):
    try:
        csrf_token = await get_csrf_token(session)
        if not csrf_token:
            if await login(session):
                csrf_token = await get_csrf_token(session)
            if not csrf_token:
                return []
        
        headers = SMS_HEADERS.copy()
        headers["X-CSRF-TOKEN"] = csrf_token
        payload = f"_token={csrf_token}&from=&to="
        
        async with session.post(SMS_LIST_URL, headers=headers, data=payload, timeout=30) as response:
            response.raise_for_status()
            content_encoding = response.headers.get('Content-Encoding', '')
            if content_encoding == 'br' and brotli:
                content = await response.read()
                response_text = brotli.decompress(content).decode('utf-8')
            else:
                response_text = await response.text()
        
        soup = BeautifulSoup(response_text, 'html.parser')
        items = soup.find_all('div', class_='item')
        sms_list = []
        sms_cache = await load_sms_cache()
        
        for item in items:
            try:
                range_name = item.find('div', class_='col-sm-4')
                range_name = range_name.text.strip() if range_name else "Unknown"
                count = item.find('p', string=re.compile(r'^\d+$'))
                count = count.text if count else "0"
                
                numbers = await fetch_numbers(session, range_name, csrf_token)
                
                for num in numbers:
                    try:
                        sms_details = await fetch_sms_details(session, num, range_name, csrf_token)
                        message_id = f"{num}_{sms_details.get('message', '')[:50]}"
                        if message_id in sms_cache:
                            continue
                        
                        country_name = extract_country(range_name)
                        country_emoji = get_country_emoji(country_name)
                        sms_entry = {
                            "range": range_name,
                            "count": count,
                            "country": country_name,
                            "country_emoji": country_emoji,
                            "service": sms_details.get('service', 'Unknown'),
                            "number": num,
                            "otp": extract_otp(sms_details.get('message', '')),
                            "full_message": sms_details.get('message', 'No message available'),
                            "message_id": message_id
                        }
                        sms_list.append(sms_entry)
                        sms_cache[message_id] = {"timestamp": datetime.now().isoformat()}
                        await save_sms_cache(sms_cache)
                    except Exception as e:
                        LOGGER.error(f"Error processing number {num}: {e}")
                        continue
            except Exception as e:
                LOGGER.error(f"Error processing item: {e}")
                continue
        
        return sms_list
    except Exception as e:
        LOGGER.error(f"Error in fetch_sms: {e}")
        return []

async def fetch_numbers(session, range_name, csrf_token):
    try:
        headers = SMS_HEADERS.copy()
        headers["X-CSRF-TOKEN"] = csrf_token
        payload = f"_token={csrf_token}&start=&end=&range={range_name}"
        async with session.post(SMS_NUMBERS_URL, headers=headers, data=payload, timeout=30) as response:
            response.raise_for_status()
            content_encoding = response.headers.get('Content-Encoding', '')
            if content_encoding == 'br' and brotli:
                content = await response.read()
                response_text = brotli.decompress(content).decode('utf-8')
            else:
                response_text = await response.text()
            soup = BeautifulSoup(response_text, 'html.parser')
            number_divs = soup.find_all('div', class_='col-sm-4')
            return [div.text.strip() for div in number_divs if div.text.strip()]
    except Exception as e:
        LOGGER.error(f"Error fetching numbers: {e}")
        return []

async def fetch_sms_details(session, number, range_name, csrf_token):
    max_retries = 3
    delay = 5
    for attempt in range(max_retries):
        try:
            headers = SMS_HEADERS.copy()
            headers["X-CSRF-TOKEN"] = csrf_token
            payload = f"_token={csrf_token}&start=&end=&Number={number}&Range={range_name}"
            async with session.post(SMS_DETAILS_URL, headers=headers, data=payload, timeout=30) as response:
                response.raise_for_status()
                content_encoding = response.headers.get('Content-Encoding', '')
                if content_encoding == 'br' and brotli:
                    content = await response.read()
                    response_text = brotli.decompress(content).decode('utf-8')
                else:
                    response_text = await response.text()
                soup = BeautifulSoup(response_text, 'html.parser')
                message_divs = soup.select('div.col-9.col-sm-6 p.mb-0.pb-0')
                messages = [div.text.strip() for div in message_divs] if message_divs else ["No message found"]
                service_div = soup.find('div', class_='col-sm-4')
                service = service_div.text.strip().replace('CLI', '').strip() if service_div else "Unknown"
                
                sms_details = []
                for message in messages:
                    service_from_message = extract_service(message)
                    if service_from_message != "Unknown":
                        service = service_from_message
                    sms_details.append({"message": message, "service": service})
                
                return sms_details[0] if sms_details else {"message": "No message found", "service": "Unknown"}
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                LOGGER.warning(f"Too Many Requests (429) on attempt {attempt + 1} for {number}, retrying in {delay} seconds")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            LOGGER.error(f"Error fetching SMS details for {number}: {e}")
            return {"message": "No message found", "service": "Unknown"}
        except Exception as e:
            LOGGER.error(f"Error fetching SMS details for {number}: {e}")
            return {"message": "No message found", "service": "Unknown"}
    LOGGER.error(f"Failed to fetch SMS details for {number} after {max_retries} retries")
    return {"message": "No message found", "service": "Unknown"}

def extract_country(range_name):
    country = range_name.split()[0].capitalize() if range_name and len(range_name.split()) > 1 else "Unknown"
    return country

def extract_service(message):
    for service, pattern in SERVICE_PATTERNS.items():
        if re.search(pattern, message, re.IGNORECASE):
            return service
    return "Unknown"

def extract_otp(text):
    match = re.search(r'\b(\d{4,6}|\d{3}\s\d{3})\b|verification code: (\w+)', text, re.IGNORECASE)
    return match.group(0) if match else "No OTP found"

async def send_sms_to_telegram(client, sms):
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        date = datetime.now().strftime("%d-%m-%Y")
        country_emoji = sms['country_emoji']
        country = html.escape(sms['country'])
        service = html.escape(sms['service'])
        formatted_otp = html.escape(format_otp_with_spaces(sms['otp']))
        number = html.escape(sms['number'])
        full_message = html.escape(sms['full_message'])
        message = (
            f"**{country_emoji} {country} SMS OTP Received Successfully ✅**\n"
            "**━━━━━━━━━━━━━━━━━━━━━━━**\n"
            f"**⚡️ OTP Code :** `{formatted_otp}`\n"
            f"**⏰ Time:** `{timestamp}`\n"
            f"**📅 Date:** `{date}`\n"
            f"**💰 Service:** `{service}`\n"
            f"**💸 Payment:** `Paid`\n"
            f"**🔍 Phone Number:** `{number}`\n"
            f"**❤️ OTP Message :** `{full_message}`\n"
            "**━━━━━━━━━━━━━━━━━━━━━━━**\n"
            "**Note: Don't Spam Here Just Wait Else Ban 🚫**"
        )
        tasks = []
        for chat_id in CHAT_IDS:
            try:
                await client.get_entity(chat_id)
                tasks.append(client.send_message(
                    chat_id,
                    message,
                    parse_mode='md',
                    buttons=ReplyInlineMarkup([
                        KeyboardButtonRow([
                            KeyboardButtonCopy("Copy OTP Code 🗒", formatted_otp)
                        ])
                    ])
                ))
            except ChatWriteForbiddenError:
                LOGGER.error(f"Bot cannot send messages to chat {chat_id}: Write access forbidden")
            except PeerIdInvalidError:
                LOGGER.error(f"Invalid peer ID for chat {chat_id}")
            except Exception as e:
                LOGGER.error(f"Error checking chat {chat_id}: {e}")
        await asyncio.gather(*tasks, return_exceptions=True)
    except FloodWaitError as e:
        LOGGER.warning(f"Flood wait error: Waiting {e.seconds} seconds")
        await asyncio.sleep(e.seconds + 1)
        tasks = []
        for chat_id in CHAT_IDS:
            try:
                await client.get_entity(chat_id)
                tasks.append(client.send_message(
                    chat_id,
                    message,
                    parse_mode='md',
                    buttons=ReplyInlineMarkup([
                        KeyboardButtonRow([
                            KeyboardButtonCopy("Copy OTP Code 🗒", formatted_otp)
                        ])
                    ])
                ))
            except ChatWriteForbiddenError:
                LOGGER.error(f"Bot cannot send messages to chat {chat_id}: Write access forbidden")
            except PeerIdInvalidError:
                LOGGER.error(f"Invalid peer ID for chat {chat_id}")
            except Exception as e:
                LOGGER.error(f"Error checking chat {chat_id}: {e}")
        await asyncio.gather(*tasks, return_exceptions=True)
    except PeerIdInvalidError:
        LOGGER.error(f"Chat not found: {CHAT_IDS}")
    except Exception as e:
        LOGGER.error(f"Error sending OTP message: {e}")

async def send_start_alert(client):
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        date = datetime.now().strftime("%d-%m-%Y")
        message = (
            "**Smart OTP Bot Started Successfully ✅**\n"
            "**━━━━━━━━━━━━━━━━━━━━━━**\n"
            f"**⏰ Time:** `{timestamp}`\n"
            f"**📅 Date:** `{date}`\n"
            "**💰 Traffic:** Running.....📡\n"
            "**📩 Otp Scrapper:** Running...🔍\n"
            "**━━━━━━━━━━━━━━━━━━━━━━**\n"
            "**Don't Spam Here Just Wait For OTP ❌**"
        )
        user_name = get_display_name(await client.get_entity(OWNER_ID))
        tasks = []
        recipients = CHAT_IDS + [OWNER_ID]
        for chat_id in recipients:
            try:
                if chat_id in CHAT_IDS:
                    await client.get_entity(chat_id)
                tasks.append(client.send_message(
                    chat_id,
                    message,
                    parse_mode='md',
                    buttons=ReplyInlineMarkup([
                        KeyboardButtonRow([
                            InputKeyboardButtonUserProfile("👨🏻‍💻 Developer", await client.get_input_entity(OWNER_ID)),
                            Button.url("Updates Channel", UPDATE_CHANNEL_URL)
                        ])
                    ])
                ))
            except ChatWriteForbiddenError:
                LOGGER.error(f"Bot cannot send messages to chat {chat_id}: Write access forbidden")
            except PeerIdInvalidError:
                LOGGER.error(f"Invalid peer ID for chat {chat_id}")
            except Exception as e:
                LOGGER.error(f"Error checking chat {chat_id}: {e}")
        await asyncio.gather(*tasks, return_exceptions=True)
    except FloodWaitError as e:
        LOGGER.warning(f"Flood wait error: Waiting {e.seconds} seconds")
        await asyncio.sleep(e.seconds + 1)
        tasks = []
        for chat_id in recipients:
            try:
                if chat_id in CHAT_IDS:
                    await client.get_entity(chat_id)
                tasks.append(client.send_message(
                    chat_id,
                    message,
                    parse_mode='md',
                    buttons=ReplyInlineMarkup([
                        KeyboardButtonRow([
                            InputKeyboardButtonUserProfile("👨🏻‍💻 Developer", await client.get_input_entity(OWNER_ID)),
                            Button.url("Updates Channel", UPDATE_CHANNEL_URL)
                        ])
                    ])
                ))
            except ChatWriteForbiddenError:
                LOGGER.error(f"Bot cannot send messages to chat {chat_id}: Write access forbidden")
            except PeerIdInvalidError:
                LOGGER.error(f"Invalid peer ID for chat {chat_id}")
            except Exception as e:
                LOGGER.error(f"Error checking chat {chat_id}: {e}")
        await asyncio.gather(*tasks, return_exceptions=True)
    except PeerIdInvalidError:
        LOGGER.error(f"Chat not found: {recipients}")
    except Exception as e:
        LOGGER.error(f"Error sending start alert: {e}")

def setup_otp_handler(app: TelegramClient):
    async def run_sms_monitor():
        async with aiohttp.ClientSession() as session:
            await send_start_alert(app)
            last_login_time = time.time()
            if await login(session):
                LOGGER.info("Login successful, starting monitoring...")
                while True:
                    try:
                        success, last_login_time = await refresh_session(session, last_login_time)
                        if not success:
                            LOGGER.error("Session refresh failed, retrying...")
                            await asyncio.sleep(10)
                            continue
                        sms_list = await fetch_sms(session)
                        if sms_list:
                            LOGGER.info(f"Found {len(sms_list)} new SMS messages")
                            for i in range(0, len(sms_list), 20):
                                batch = sms_list[i:i+20]
                                tasks = []
                                for sms in batch:
                                    if sms['full_message'] != "No message found" and sms['otp'] != "No OTP found":
                                        if await check_and_save_otp(sms['number'], sms['otp'], sms['message_id']):
                                            LOGGER.info(f"Sending OTP for {sms['number']}: {sms['otp']}")
                                            tasks.append(send_sms_to_telegram(app, sms))
                                await asyncio.gather(*tasks, return_exceptions=True)
                                if i + 20 < len(sms_list):
                                    LOGGER.info("Processed batch, waiting 3 seconds...")
                                    await asyncio.sleep(3)
                        else:
                            LOGGER.info("No new SMS messages found")
                        await asyncio.sleep(5)
                    except Exception as e:
                        LOGGER.error(f"Error in main loop: {e}")
                        await asyncio.sleep(10)
            else:
                LOGGER.error("Initial login failed")
    app.loop.create_task(run_sms_monitor())