import os
import requests
import json

# 1. إعدادات القنوات والأسرار
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
    """جلب آخر كوكيز مخزن في الخزنة كنقطة انطلاق للمستقبل"""
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"⚠️ تنبيه: تعذر جلب الكوكيز من الخزنة ({e})")
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    """تحديث الكوكيز من سيرفرات OK.ru"""
    # الأولوية القصوى للكوكيز من الخزنة (للاستمرار)، وإذا كان فارغاً نستخدم السيكرت (للبداية)
    base_cookie = last_kv_cookie if last_kv_cookie else secret_cookie
    
    if not base_cookie:
        print(f"❌ خطأ: لا يوجد كوكيز أساسي للقناة {video_id} (لا في السيكرت ولا في الخزنة).")
        return None

    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://ok.ru/"
    }
    
    session = requests.Session()
    # تحويل نص الكوكيز الحالي لقاموس وإدخاله في الجلسة
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in base_cookie.split(';') if '=' in c}
    session.cookies.update(c_dict)
    
    try:
        # الهجوم على السيرفر لتحديث الجلسة
        response = session.get(url, headers=headers, timeout=20)
        
        # اكتشاف الرفض أو الحظر
        if response.status_code in [403, 404]:
            print(f"❌ تم الرفض من OK.ru للقناة {video_id} (Status {response.status_code}).")
            return None
            
        new_cookies = session.cookies.get_dict()
        
        # هندسة نظيفة: دمج الكوكيز القديم مع الجديد لضمان عدم فقدان AUTHCODE أبداً
        merged_cookies = c_dict.copy()
        merged_cookies.update(new_cookies)
        
        final_cookie_string = "; ".join([f"{k}={v}" for k, v in merged_cookies.items()])
        return final_cookie_string
        
    except Exception as e:
        print(f"❌ فشل الاتصال بقناة {video_id}: {str(e)}")
        return None

# 1. جلب البيانات الحالية من الخزنة
kv_data = get_last_cookies_from_kv()
final_data = {}
success_count = 0

print("🚀 بدء محرك APiX لتحديث الكوكيز لـ 13 قناة...")
for cid, secret_c in CHANNELS_MAP.items():
    print(f"🔄 جاري معالجة القناة: {cid}")
    last_c = kv_data.get(cid)
    
    # تجربة التحديث الحي
    updated_cookie = refresh_channel(cid, secret_c, last_c)
    
    if updated_cookie:
        final_data[cid] = updated_cookie
        success_count += 1
    else:
        # إذا فشل التحديث (بسبب الـ IP مثلاً)، نحتفظ بآخر كوكيز شغال لكي لا ينقطع البث فجأة
        print(f"⚠️ الاحتفاظ بالكوكيز القديم للقناة {cid} كخط دفاع أخير لتجنب التوقف.")
        final_data[cid] = last_c if last_c else secret_c

# 2. حفظ البيانات المحدثة في الخزنة
if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print(f"✅ إنجاز: تم حفظ بيانات {success_count} قناة في الخزنة بنجاح.")
        # إذا لم ينجح تحديث كل القنوات، نجبر جيت هاب على إظهار علامة حمراء للتنبيه
        if success_count < len(CHANNELS_MAP):
            print("⚠️ ملاحظة: تم التحديث جزئياً. بعض القنوات واجهت رفضاً من المصدر.")
            exit(1)
    else:
        print(f"❌ كارثة: فشل رفع البيانات للخزنة: {res.text}")
        exit(1)
else:
    print("❌ لم يتم جمع أي بيانات لحفظها!")
    exit(1)
