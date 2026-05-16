import requests
import json
import os
import re
import html

# المعرفات الخاصة بقنوات APiX الستة
CHANNELS_MAP = {
    "14574023089903": os.getenv('COOKIE_CH1'), # APiX 1
    "14639543099119": os.getenv('COOKIE_CH2'), # APiX 2
    "14644667621103": os.getenv('COOKIE_CH3'), # APiX 3 
    "14648750055151": os.getenv('COOKIE_CH4'), # APiX 4 
    "14648779808495": os.getenv('COOKIE_CH5'), # APiX 5 
    "14648850915055": os.getenv('COOKIE_CH6')  # APiX 6 
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
    except Exception as e:
        print(f"⚠️ خطأ أثناء جلب البيانات من KV: {e}")
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    """تحديث الكوكيز واستخراج رابط HLS مباشرة من كود مصدر الصفحة (بدون حماية TKN)"""
    # الأولوية للـ كوكيز الموجود في الخزنة، وإذا كانت فارغة نستخدم السيكرت
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    
    if not cookie_to_use:
        print(f"⚠️ تجاهل القناة {video_id}: لا يوجد كوكيز متاح.")
        return None

    # الدخول لرابط البث المباشر كمتصفح عادي
    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Cookie": cookie_to_use,
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            # فك تشفير الكيانات HTML
            page_text = html.unescape(res.text)
            
            # صيد رابط الـ HLS من وسط أكواد الصفحة باستخدام Regex
            match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+)"', page_text)
            
            if match:
                # تنظيف الرابط من الخطوط المائلة العكسية
                hls_url = match.group(1).replace('\\/', '/')
                return {
                    "cookie": cookie_to_use,
                    "url": hls_url
                }
            else:
                print(f"⚠️ لم يتم العثور على رابط HLS. قد يكون البث متوقفاً أو الكوكيز منتهي.")
        else:
            print(f"⚠️ خطأ في الاستجابة للقناة {video_id}: الكود {res.status_code}")
    except Exception as e:
        print(f"⚠️ فشل الاتصال بالقناة {video_id}: {e}")
        
    return None

def main():
    print("🚀 Starting APiX Auto Fisher (Scraping 6 Channels)...")
    last_data = get_last_cookies_from_kv()
    
    final_data = {}
    
    for vid, secret_cookie in CHANNELS_MAP.items():
        print(f"\n🔄 جاري معالجة القناة ID: {vid} ...")
        
        channel_info = last_data.get(vid, {})
        last_kv_cookie = channel_info.get("cookie", "") if isinstance(channel_info, dict) else ""
        
        channel_data = refresh_channel(vid, secret_cookie, last_kv_cookie)
        
        if channel_data:
            final_data[vid] = channel_data
            print(f"✅ نجاح: تم استخراج الرابط للقناة {vid}")
        else:
            print(f"❌ فشل: لم نتمكن من معالجة القناة {vid}")
            
    if final_data:
        print("\n📤 جاري رفع القائمة المحدثة إلى Cloudflare KV...")
        payload = json.dumps(final_data)
        
        upload_res = requests.put(KV_URL, headers=CF_HEADERS, data=payload)
        
        if upload_res.status_code == 200:
            print("🎉 تم التحديث بنجاح! (KV Updated Successfully!)")
        else:
            print(f"⚠️ فشل الرفع لـ KV: {upload_res.status_code} - {upload_res.text}")
    else:
        print("\n⚠️ لا توجد أي قنوات صالحة لرفعها. تأكد من صحة الكوكيز في الأسرار.")

if __name__ == "__main__":
    main()
