import requests
import json
import os

# المعرفات الخاصة بجميع القنوات (13 قناة الآن)
CHANNELS_MAP = {
    # القنوات الأساسية الستة
    "14574023089903": os.getenv('COOKIE_CH1'),
    "14639543099119": os.getenv('COOKIE_CH2'),
    "14644667621103": os.getenv('COOKIE_CH3'),
    "14648750055151": os.getenv('COOKIE_CH4'),
    "14648779808495": os.getenv('COOKIE_CH5'),
    "14648850915055": os.getenv('COOKIE_CH6'),
    
    # قنوات الأفلام الأربعة
    "14649045950191": os.getenv('COOKIE_CH_MOVIE_1'),
    "14649095954159": os.getenv('COOKIE_CH_MOVIE_2'),
    "14649204874991": os.getenv('COOKIE_CH_MOVIE_3'),
    "14649226370799": os.getenv('COOKIE_CH_MOVIE_4'),
    
    # قناتك الخاصة للأفلام
    "14611275587311": os.getenv('COOKIE_CH_ME_MOVIE_1'),

    # القناتان الخاصتان الجديدتان (APiX 1 & APiX 2)
    "14692414791407": os.getenv('COOKIE_APIX_1'),
    "14692421476079": os.getenv('COOKIE_APIX_2')
}

# إعدادات Cloudflare المستخرجة من الأسرار
CF_ACC = os.getenv('CF_ACCOUNT_ID')
CF_NS = os.getenv('CF_KV_NAMESPACE')
CF_TOKEN = os.getenv('CF_API_TOKEN')
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/storage/kv/namespaces/{CF_NS}/values/CHANNELS_COOKIES"
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

def get_last_cookies_from_kv():
    """جلب آخر كوكيز مخزن في الخزنة لضمان استمرار الجلسة"""
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    """تحديث الكوكيز بناءً على آخر حالة ناجحة"""
    # الأولوية للـ كوكيز الموجود في الخزنة، وإذا كانت فارغة نستخدم السيكرت
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    
    if not cookie_to_use:
        return None

    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Referer": "https://ok.ru/"
    }
    
    session = requests.Session()
    # تحويل نص الكوكيز إلى قاموس للجلسة
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(c_dict)
    
    try:
        session.get(url, headers=headers, timeout=20)
        # استخراج الكوكيز الجديد المحدث
        new_cookies = session.cookies.get_dict()
        if new_cookies:
            return "; ".join([f"{k}={v}" for k, v in new_cookies.items()])
        else:
            return cookie_to_use
    except:
        return cookie_to_use

# 1. جلب البيانات الحالية من الخزنة
kv_data = get_last_cookies_from_kv()

# 2. تحديث كل قناة بناءً على كوكيزها الخاص
final_data = {}
print("🚀 بدء تحديث الكوكيز لـ 13 قناة...")
for cid, secret_c in CHANNELS_MAP.items():
    print(f"🔄 معالجة القناة: {cid}")
    last_c = kv_data.get(cid)
    new_c = refresh_channel(cid, secret_c, last_c)
    if new_c:
        final_data[cid] = new_c

# 3. حفظ البيانات الجديدة في الخزنة
if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print("✅ نجاح: تم تحديث الخزنة بكوكيز جديد لكل القنوات الـ 13.")
    else:
        print(f"❌ فشل تحديث الخزنة: {res.text}")
