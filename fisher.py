import requests
import json
import os
import time
import random

# قائمة الـ User-Agents لتشتيت الحماية
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"
]

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
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"⚠️ تعذر الوصول لخزنة KV: {e}")
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie, current_ua):
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    if not cookie_to_use:
        return None, False

    url = f"https://ok.ru/live/{video_id}"
    headers = {"User-Agent": current_ua, "Referer": "https://ok.ru/"}
    
    session = requests.Session()
    # تفكيك الكوكيز القديم إلى قاموس (Dict)
    old_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(old_dict)
    
    try:
        response = session.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            new_cookies_dict = session.cookies.get_dict()
            
            # فحص صارم: هل أصدر السيرفر كوكيز جديدة فعلاً؟
            if not new_cookies_dict:
                print(f"   ⚠️ السيرفر سمح بالدخول (200) ولكنه لم يعطنا أي كوكيز جديد! (الكوكيز نفسه)")
                return cookie_to_use, False
                
            merged = old_dict.copy()
            merged.update(new_cookies_dict)
            
            # التأكد النهائي من أن القاموس المدمج يختلف عن القديم
            if merged == old_dict:
                print(f"   ⚠️ السيرفر رد بكوكيز متطابق تماماً مع القديم. (لم يحدث تغيير)")
                return cookie_to_use, False
            else:
                print(f"   ✅ نجاح حقيقي: تم استلام كوكيز جديد ومختلف من السيرفر!")
                return "; ".join([f"{k}={v}" for k, v in merged.items()]), True
        else:
            print(f"   ❌ الموقع رفض الطلب (Status {response.status_code}).")
            return cookie_to_use, False
            
    except Exception as e:
        print(f"   ❌ خطأ اتصال بـ OK.ru: {e}")
        return cookie_to_use, False

# ==========================================
# التنفيذ الرئيسي (The Engine)
# ==========================================
print("🚀 بدء محرك APiX للفحص والتحديث العميق...")
kv_data = get_last_cookies_from_kv()
final_data = {}
changes_count = 0

channel_ids = list(CHANNELS_MAP.keys())

for i, cid in enumerate(channel_ids):
    print(f"\n[{i+1}/{len(channel_ids)}] جاري معالجة القناة: {cid}")
    
    ua_index = (i // 2) % len(USER_AGENTS)
    current_ua = USER_AGENTS[ua_index]
    
    secret_c = CHANNELS_MAP[cid]
    last_c = kv_data.get(cid)
    
    # استدعاء دالة التحديث التي ترجع (نص الكوكيز، هل تغير أم لا)
    new_c, is_changed = refresh_channel(cid, secret_c, last_c, current_ua)
    
    if new_c:
        final_data[cid] = new_c
        if is_changed:
            changes_count += 1
        
    if i < len(channel_ids) - 1:
        delay = random.randint(4, 7)
        print(f"   ⏳ استراحة {delay} ثوانٍ للتمويه...")
        time.sleep(delay)

print(f"\n📊 إحصائية الفحص: تم العثور على تغيير حقيقي في ({changes_count}) قنوات من أصل {len(channel_ids)}.")

# ==========================================
# فحص رفع البيانات لـ Cloudflare KV
# ==========================================
if final_data:
    print("🚀 جاري رفع الكوكيز لـ Cloudflare KV...")
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    
    if res.status_code == 200:
        print("✅ كلاود فلير رد بـ 200 (تم الرفع).")
        
        # الفحص المزدوج بناءً على طلبك
        print("🔍 جاري التحقق من كلاود فلير بعد الرفع للتأكد من حفظ البيانات...")
        time.sleep(3) # ننتظر قليلاً لضمان استقرار الخزنة
        verify_data = get_last_cookies_from_kv()
        
        # نأخذ أول قناة عشوائياً كعينة للفحص
        sample_cid = channel_ids[0]
        if verify_data.get(sample_cid) == final_data.get(sample_cid):
            print("✅ الفحص المزدوج سليم 100%: الكوكيز في KV يطابق الكوكيز الذي أرسلناه للتو!")
        else:
            print("❌ كارثة في KV: كلاود فلير رد بالنجاح ولكنه لم يحفظ البيانات الجديدة! (قد يكون هناك Cache أو مشكلة في الخزنة).")
            
    else:
        print(f"❌ فشل الرفع لـ Cloudflare! الخطأ: {res.text}")
else:
    print("⚠️ لا توجد أي كوكيز للرفع.")
