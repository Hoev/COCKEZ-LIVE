import requests
import json
import os
import time
import random

# 1. المعرفات الخاصة بجميع القنوات الـ 13
CHANNELS_MAP = {
    "14574023089903": os.getenv('COOKIE_CH1'),
    "14639543099119": os.getenv('COOKIE_CH2'),
    "14644667621103": os.getenv('COOKIE_CH3'),
    "14648750055151": os.getenv('COOKIE_CH4'),
    "14648779808495": os.getenv('COOKIE_CH5'),
    "14648850915055": os.getenv('COOKIE_CH6'),
    "14649045950191": os.getenv('COOKIE_CH_MOVIE_1'),
    "14649095954159": os.getenv('COOKIE_CH_MOVIE_2'),
    "14649204874991": os.getenv('COOKIE_CH_MOVIE_3'),
    "14649226370799": os.getenv('COOKIE_CH_MOVIE_4'),
    "14611275587311": os.getenv('COOKIE_CH_ME_MOVIE_1'),
    "14692414791407": os.getenv('COOKIE_APIX_1'),
    "14692421476079": os.getenv('COOKIE_APIX_2')
}

# 2. إعدادات Cloudflare
CF_ACC = os.getenv('CF_ACCOUNT_ID')
CF_NS = os.getenv('CF_KV_NAMESPACE')
CF_TOKEN = os.getenv('CF_API_TOKEN')
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/storage/kv/namespaces/{CF_NS}/values/CHANNELS_COOKIES"
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

def get_last_cookies_from_kv():
    """جلب بيانات الكوكيز الحالية من الخزنة لكي نحدثها"""
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    """الذهاب إلى OK.ru بهدوء وجلب التحديث"""
    # الأولوية لكوكيز الخزنة، وإذا كان غير موجود نأخذ السيكرت
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    
    if not cookie_to_use:
        print(f"   ⚠️ لا يوجد كوكيز أولي للقناة {video_id}")
        return None

    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://ok.ru/"
    }
    
    session = requests.Session()
    # تجهيز الكوكيز
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(c_dict)
    
    try:
        # إرسال الطلب
        response = session.get(url, headers=headers, timeout=20)
        
        # فحص صريح: هل الموقع سمح لنا بالدخول؟
        if response.status_code == 200:
            new_cookies = session.cookies.get_dict()
            # دمج الكوكيز القديم مع الجديد لكي لا نفقد الـ AUTHCODE
            merged = c_dict.copy()
            merged.update(new_cookies)
            print(f"   ✅ تم جلب كوكيز جديد للقناة {video_id} (Status 200)")
            return "; ".join([f"{k}={v}" for k, v in merged.items()])
        else:
            # إذا طردنا الموقع، نرجع الكوكيز القديم لكي لا يخرب البث
            print(f"   ❌ الموقع رفض الطلب (Status {response.status_code}). سيتم الاحتفاظ بالكوكيز القديم.")
            return cookie_to_use
            
    except Exception as e:
        print(f"   ❌ حدث خطأ في الاتصال: {e}")
        return cookie_to_use

# --- بداية التنفيذ الفعلي ---
print("🚀 جاري الاتصال بخزنة Cloudflare لجلب البيانات السابقة...")
kv_data = get_last_cookies_from_kv()
final_data = {}

print(f"🔄 بدء تحديث {len(CHANNELS_MAP)} قنوات بهدوء لتجنب الحظر...")

for index, (cid, secret_c) in enumerate(CHANNELS_MAP.items(), 1):
    print(f"\n[{index}/{len(CHANNELS_MAP)}] معالجة القناة: {cid}")
    last_c = kv_data.get(cid)
    
    # تحديث القناة
    new_c = refresh_channel(cid, secret_c, last_c)
    if new_c:
        final_data[cid] = new_c
        
    # السر هنا: التوقف (Sleep) من 5 إلى 8 ثوانٍ بين كل قناة وأخرى لكي نبدو كالمستخدم الطبيعي
    if index < len(CHANNELS_MAP): # لا ننتظر بعد آخر قناة
        delay = random.randint(5, 8)
        print(f"   ⏳ انتظار {delay} ثوانٍ لتجنب حظر OK.ru...")
        time.sleep(delay)

print("\n🚀 جاري رفع الكوكيز المحدثة إلى Cloudflare KV...")
if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print("✅ إنجاز: تم تحديث الخزنة بنجاح! البث في أمان.")
    else:
        print(f"❌ فشل رفع البيانات إلى كلاود فلير: {res.text}")
else:
    print("⚠️ لا توجد بيانات لرفعها.")
