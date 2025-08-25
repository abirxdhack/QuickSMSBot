#Copyright @ISmartCoder
#Updates Channel t.me/TheSmartDev
LOGIN_URL = "https://www.ivasms.com/login"
SMS_LIST_URL = "https://www.ivasms.com/portal/sms/received/getsms"
SMS_NUMBERS_URL = "https://www.ivasms.com/portal/sms/received/getsms/number"
SMS_DETAILS_URL = "https://www.ivasms.com/portal/sms/received/getsms/number/sms"
SMS_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.ivasms.com/portal/sms/received",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "text/html, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Encoding": "gzip, deflate"
}
OTP_HISTORY_FILE = "otp_history.json"
SMS_CACHE_FILE = "sms_cache.json"