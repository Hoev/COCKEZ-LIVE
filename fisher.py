import requests
import json
import os
import time
import random

# ==========================================
# 1. قائمة المتصفحات (User-Agents) للتمويه
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"
]

# ==========================================
# 2. القنوات والأسرار
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
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}

def force_refresh_channel(video_id, secret_cookie, last_kv_cookie, current_ua):
    """الدالة الشرسة: تحذف التوكنات القديمة لتجبر السيرفر على إصدار توكنات جديدة"""
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    if not cookie_to_use:
        return None, False

    session = requests.Session()
    
    # 1. تفكيك الكوكيز القديم إلى قاموس (Dict)
    old_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    
    # 2. تكتيك القناص: ننسخ الكوكيز، ونمسح منه AUTHCODE و JSESSIONID
    hacked_dict = old_dict.copy()
    if 'AUTHCODE' in hacked_dict:
        del hacked_dict['AUTHCODE']
    if 'JSESSIONID' in hacked_dict:
        del hacked_dict['JSESSIONID']
        
    # نحقن الكوكيز "المقصوص" في الجلسة لكي ندخل بهويتنا ولكن بدون جلسة فعالة
    session.cookies.update(hacked_dict)
    
    main_url = f"https://ok.ru/live/{video_id}"
    deep_url = "https://ok.ru/dk?cmd=videoPlayerMetadata"
    
    get_headers = {"User-Agent": current_ua, "Referer": "https://ok.ru/"}
    post_headers = {
        "User-Agent": current_ua,
        "Referer": main_url,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://ok.ru"
    }
    payload = f"mid={video_id}&is=on&st.location=AutoplayLayerMovieRBlock%2Fvideo"

    max_retries = 4
    for attempt in range(1, max_retries + 1):
        print(f"   🔄 [محاولة {attempt}/{max_retries}] جاري التفاوض مع السيرفر...")
        
        try:
            print("   🌐 الخطوة 1: الدخول للصفحة لفتح جلسة جديدة كلياً...")
            session.get(main_url, headers=get_headers, timeout=15)
            
            print("   🔥 الخطوة 2: إرسال طلب POST العميق لاستخراج الـ AUTHCODE الجديد...")
            response = session.post(deep_url, headers=post_headers, data=payload, timeout=15)
            
            if response.status_code == 200:
                new_cookies_dict = session.cookies.get_dict()
                
                # ندمج الكوكيز الجديد مع الأصلي (الذي يحتوي على هويتنا الكاملة)
                merged = old_dict.copy()
                merged.update(new_cookies_dict)
                
                if merged.get('AUTHCODE') == old_dict.get('AUTHCODE'):
                    print("   ⚠️ السيرفر عنيد وأعطانا نفس الـ AUTHCODE القديم.")
                    if attempt < max_retries:
                        wait_time = random.randint(3, 5)
                        print(f"   ⏳ سننتظر {wait_time} ثوانٍ ونهاجم مرة أخرى...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print("   ❌ استنفدنا المحاولات. سيتم إرجاع الكوكيز القديم.")
                        return cookie_to_use, False
                else:
                    print("   🎉 اختراق ناجح! السيرفر رضخ وأعطانا توكنات جديدة تماماً.")
                    return "; ".join([f"{k}={v}" for k, v in merged.items()]), True
            else:
                print(f"   ❌ فشلت! السيرفر رفض الطلب (Status {response.status_code}).")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return cookie_to_use, False
                
        except Exception as e:
            print(f"   ❌ حدث خطأ غير متوقع: {e}")
            if attempt < max_retries:
                time.sleep(3)
                continue
            return cookie_to_use, False

# ==========================================
# التنفيذ الرئيسي
# ==========================================
print("🚀 بدء محرك APiX الهجومي للفحص والتحديث العميق...")
kv_data = get_last_cookies_from_kv()
if kv_data:
    print("📥 تم جلب كوكيز الخزنة بنجاح لنقارن به.")

final_data = {}
changes_count = 0
channel_ids = list(CHANNELS_MAP.keys())

for i, cid in enumerate(channel_ids):
    print(f"\n[{i+1}/{len(channel_ids)}] جاري اقتحام القناة: {cid}")
    
    ua_index = (i // 2) % len(USER_AGENTS)
    current_ua = USER_AGENTS[ua_index]
    print(f"   🕵️ تغيير المتصفح إلى: رقم {ua_index + 1}")
    
    secret_c = CHANNELS_MAP[cid]
    last_c = kv_data.get(cid)
    
    new_c, is_changed = force_refresh_channel(cid, secret_c, last_c, current_ua)
    
    if new_c:
        final_data[cid] = new_c
        if is_changed:
            changes_count += 1
            
    if i < len(channel_ids) - 1:
        delay = random.randint(3, 6)
        print(f"   💤 استراحة تكتيكية {delay} ثوانٍ للتمويه...")
        time.sleep(delay)

print(f"\n📊 التقرير النهائي: تم إجبار السيرفر على تغيير الكوكيز في ({changes_count}) قنوات.")

if final_data:
    print("🚀 جاري حفر الكوكيز النهائي في Cloudflare KV...")
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print("✅ إنجاز: تم حفظ البيانات في الخزنة بنجاح.")
        
        # فحص مزدوج للتأكد من كلاود فلير
        time.sleep(3)
        verify_data = get_last_cookies_from_kv()
        sample_cid = channel_ids[0]
        if verify_data.get(sample_cid) == final_data.get(sample_cid):
            print("✅ الفحص المزدوج سليم 100%: الكوكيز في KV يطابق الكوكيز الجديد!")
        else:
            print("❌ مشكلة في KV: كلاود فلير لم يحفظ البيانات الجديدة بالرغم من النجاح!")
    else:
        print(f"❌ فشل الحفظ في كلاود فلير: {res.text}")
else:
    print("⚠️ لا يوجد بيانات ليتم حفظها.")
