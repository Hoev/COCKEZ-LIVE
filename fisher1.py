import requests
import json
import os
import time

# متصفح مخصص لهذا الملف (ويندوز كروم)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 5 قنوات
CHANNELS_MAP = {
    "14574023089903": os.getenv('COOKIE_CH1'),
    "14639543099119": os.getenv('COOKIE_CH2'),
    "14644667621103": os.getenv('COOKIE_CH3'),
    "14648750055151": os.getenv('COOKIE_CH4'),
    "14648779808495": os.getenv('COOKIE_CH5')
}

CF_ACC = os.getenv('CF_ACCOUNT_ID')
CF_NS = os.getenv('CF_KV_NAMESPACE')
CF_TOKEN = os.getenv('CF_API_TOKEN')
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/storage/kv/namespaces/{CF_NS}/values/CHANNELS_COOKIES"
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

def get_last_cookies_from_kv():
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200: return res.json()
    except: pass
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    if not cookie_to_use: return None
    url = f"https://ok.ru/live/{video_id}"
    headers = {"User-Agent": USER_AGENT, "Referer": "https://ok.ru/"}
    session = requests.Session()
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(c_dict)
    try:
        response = session.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            new_cookies = session.cookies.get_dict()
            return "; ".join([f"{k}={v}" for k, v in new_cookies.items()])
        return cookie_to_use
    except:
        return cookie_to_use

print("🚀 بدء تشغيل fisher1.py (أول 5 قنوات)...")
kv_data = get_last_cookies_from_kv()
final_data = kv_data.copy() # نسخ القديم لكي لا نحذف القنوات الأخرى

for cid, secret_c in CHANNELS_MAP.items():
    last_c = kv_data.get(cid)
    new_c = refresh_channel(cid, secret_c, last_c)
    if new_c: final_data[cid] = new_c
    time.sleep(2) # راحة بسيطة جداً

if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200: print("✅ نجاح: تم تحديث الخزنة من fisher1.")
    else: print(f"❌ فشل: {res.text}")
