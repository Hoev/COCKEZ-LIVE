import requests
import json
import os
import time

# متصفح مخصص لهذا الملف (لينكس فايرفوكس)
USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"

# 4 قنوات متبقية
CHANNELS_MAP = {
    "14649226370799": os.getenv('COOKIE_CH_MOVIE_4'),
    "14611275587311": os.getenv('COOKIE_CH_ME_MOVIE_1'),
    "14692414791407": os.getenv('COOKIE_APIX_1'),
    "14692421476079": os.getenv('COOKIE_APIX_2')
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

print("🚀 بدء تشغيل fisher3.py (الـ 4 قنوات الأخيرة)...")
kv_data = get_last_cookies_from_kv()
final_data = kv_data.copy()

for cid, secret_c in CHANNELS_MAP.items():
    last_c = kv_data.get(cid)
    new_c = refresh_channel(cid, secret_c, last_c)
    if new_c: final_data[cid] = new_c
    time.sleep(2)

if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200: print("✅ نجاح: تم تحديث الخزنة من fisher3.")
    else: print(f"❌ فشل: {res.text}")
