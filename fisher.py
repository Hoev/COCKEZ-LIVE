import requests
import json
import os
import time
import random

# ==========================================
# 1. قائمة بـ 6 User-Agents مختلفة لتخطي الحظر
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", # ويندوز كروم
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", # ماك كروم
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36", # لينكس كروم
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0", # ويندوز فايرفوكس
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0", # ماك فايرفوكس
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0" # أوبونتو فايرفوكس
]

# ==========================================
# 2. المعرفات الخاصة بجميع القنوات الـ 13
# ==========================================
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

CF_ACC = os.getenv('CF_ACCOUNT_ID')
CF_NS = os.getenv('CF_KV_NAMESPACE')
CF_TOKEN = os.getenv('CF_API_TOKEN')
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/storage/kv/namespaces/{CF_NS}/values/CHANNELS_COOKIES"
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

def get_last_cookies_from_kv():
    """الوصول لخزنة Cloudflare وإخبارك بالنتيجة صراحة"""
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            print("📥 تم الاتصال بـ Cloudflare KV بنجاح وجلب البيانات السابقة.")
            return res.json()
        else:
            print(f"⚠️ فشل الاتصال بخزنة KV (الخطأ: {res.status_code}). سيتم الاعتماد على الأسرار (Secrets).")
    except Exception as e:
        print(f"⚠️ تعذر الوصول لخزنة KV بسبب مشكلة في الشبكة: {e}")
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie, current_ua):
    """تحديث الكوكيز مع طباعة التفاصيل صراحة"""
    
    # تحديد المصدر بصراحة وإخبارك به
    if last_kv_cookie:
        source_name = "Cloudflare KV"
        cookie_to_use = last_kv_cookie
    elif secret_cookie:
        source_name = "GitHub Secrets"
        cookie_to_use = secret_cookie
    else:
        print(f"   ❌ لا يوجد أي كوكيز (لا في KV ولا في Secrets) للقناة {video_id}!")
        return None

    print(f"   🔍 المصدر الأساسي المستخدم: {source_name}")

    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": current_ua,
        "Referer": "https://ok.ru/"
    }
    
    session = requests.Session()
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(c_dict)
    
    try:
        response = session.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            new_cookies = session.cookies.get_dict()
            merged = c_dict.copy()
            merged.update(new_cookies)
            print(f"   ✅ نجاح: تم تحديث الكوكيز من OK.ru (Status 200)")
            return "; ".join([f"{k}={v}" for k, v in merged.items()])
        else:
            print(f"   ⚠️ تحذير: OK.ru رفض التحديث (Status {response.status_code}).")
            print(f"   🛡️ سيتم إعادة استخدام الكوكيز القديم من [{source_name}] لحماية المشروع.")
            return cookie_to_use
            
    except Exception as e:
        print(f"   ❌ خطأ اتصال بـ OK.ru: {e}")
        print(f"   🛡️ سيتم إعادة استخدام الكوكيز القديم من [{source_name}] لحماية المشروع.")
        return cookie_to_use

# ==========================================
# 3. التشغيل
# ==========================================
print("🚀 بدء تشغيل محرك APiX الذكي...")
kv_data = get_last_cookies_from_kv()
final_data = {}

# قائمة المفاتيح لكي نمر عليها بالترتيب (مهمة لتوزيع الـ User-Agents)
channel_ids = list(CHANNELS_MAP.keys())

for i, cid in enumerate(channel_ids):
    print(f"\n[{i+1}/{len(channel_ids)}] جاري معالجة القناة: {cid}")
    
    # اختيار User-Agent متغير كل قناتين
    ua_index = (i // 2) % len(USER_AGENTS)
    current_ua = USER_AGENTS[ua_index]
    
    secret_c = CHANNELS_MAP[cid]
    last_c = kv_data.get(cid)
    
    # محاولة التحديث
    new_c = refresh_channel(cid, secret_c, last_c, current_ua)
    
    if new_c:
        final_data[cid] = new_c
        
    # فاصل زمني عشوائي (Sleep) لتجنب الحظر
    if i < len(channel_ids) - 1:
        delay = random.randint(4, 7)
        print(f"   ⏳ استراحة {delay} ثوانٍ للتمويه...")
        time.sleep(delay)

print("\n🚀 جاري حفر البيانات النهائية في Cloudflare KV...")
if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print("✅ إنجاز: تمت عملية الرفع لـ Cloudflare بنجاح تام!")
    else:
        print(f"❌ كارثة: فشل الرفع لـ Cloudflare! الخطأ: {res.text}")
else:
    print("⚠️ لا توجد أي كوكيز لرفعها.")
