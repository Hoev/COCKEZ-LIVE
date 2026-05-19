import requests
import json
import os

# ====================================================================
# 1. جدول القنوات: هنا يمكنك إضافة أو تعديل أي قناة مستقبلاً
# كل سطر يحتوي على (معرف الفيديو داخل الموقع) : (اسم المتغير المخزن في أسرار جيت هاب)
# ====================================================================
CHANNELS_MAP = {
    # --- القنوات الرياضية والأساسية الستة ---
    "14574023089903": os.getenv('COOKIE_CH1'),
    "14639543099119": os.getenv('COOKIE_CH2'),
    "14644667621103": os.getenv('COOKIE_CH3'),
    "14648750055151": os.getenv('COOKIE_CH4'),
    "14648779808495": os.getenv('COOKIE_CH5'),
    "14648850915055": os.getenv('COOKIE_CH6'),
    
    # --- قنوات الأفلام الأربعة ---
    "14649045950191": os.getenv('COOKIE_CH_MOVIE_1'),
    "14649095954159": os.getenv('COOKIE_CH_MOVIE_2'),
    "14649204874991": os.getenv('COOKIE_CH_MOVIE_3'),
    "14649226370799": os.getenv('COOKIE_CH_MOVIE_4'),
    
    # --- قناتك الخاصة للأفلام ---
    "14611275587311": os.getenv('COOKIE_CH_ME_MOVIE_1'),

    # --- القناتان الخاصتان الجديدتان لـ APiX ---
    "14692414791407": os.getenv('COOKIE_APIX_1'),
    "14692421476079": os.getenv('COOKIE_APIX_2')
}

# ====================================================================
# 2. إعدادات الاتصال بـ Cloudflare (تُجلب تلقائياً من الأسرار)
# ====================================================================
CF_ACC = os.getenv('CF_ACCOUNT_ID')
CF_NS = os.getenv('CF_KV_NAMESPACE')
CF_TOKEN = os.getenv('CF_API_TOKEN')

# الرابط الخاص بالوصول للمفتاح المشترك CHANNELS_COOKIES داخل الـ KV
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/storage/kv/namespaces/{CF_NS}/values/CHANNELS_COOKIES"
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

def get_last_cookies_from_kv():
    """دالة لجلب آخر كوكيز مخزن في كلاود فلير لكي نبدأ منه التحديث الدوري"""
    try:
        res = requests.get(KV_URL, headers=CF_HEADERS)
        if res.status_code == 200:
            return res.json() # إرجاع البيانات كقاموس JSON إذا نجح الجلب
    except:
        print("⚠️ لم نجد كوكيز سابق في الخزنة، سنعتمد على الأسرار كبداية.")
    return {}

def refresh_channel(video_id, secret_cookie, last_kv_cookie):
    """دالة لدخول صفحة القناة وتحديث الكوكيز تلقائياً وضمان عدم موت الجلسة"""
    # الأولوية دائماً لكوكيز الخزنة المستمر، وإذا كانت الخزنة فارغة نستخدم السيكرت البدائي
    cookie_to_use = last_kv_cookie if last_kv_cookie else secret_cookie
    
    if not cookie_to_use:
        return None

    url = f"https://ok.ru/live/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Referer": "https://ok.ru/"
    }
    
    session = requests.Session()
    
    # تحويل نص الكوكيز المجمع (String) إلى قاموس (Dict) لكي تفهمه الجلسة البرمجية
    c_dict = {c.split('=')[0].strip(): c.split('=')[1].strip() for c in cookie_to_use.split(';') if '=' in c}
    session.cookies.update(c_dict)
    
    try:
        # زيارة صفحة البث لتجديد توكنات الجلسة تلقائياً
        session.get(url, headers=headers, timeout=20)
        
        # استخراج الكوكيز الجديد الذي أرسله السيرفر بعد الزيارة
        new_cookies = session.cookies.get_dict()
        
        # دمج الكوكيز القديم مع الجديد لضمان الحفاظ على قيم مثل AUTHCODE الحساسة
        merged_cookies = c_dict.copy()
        merged_cookies.update(new_cookies)
        
        # إعادة تحويل القاموس إلى نص كوكيز جاهز للاستخدام في المواقع
        return "; ".join([f"{k}={v}" for k, v in merged_cookies.items()])
    except:
        # في حال حدوث أي خطأ في الاتصال، نرجع الكوكيز الحالي كما هو لضمان عدم توقف القناة
        return cookie_to_use

# ====================================================================
# 3. تشغيل المحرك الرئيسي والرفع
# ====================================================================

# الخطوة أ: جلب البيانات الحالية المخزنة في كلاود فلير
kv_data = get_last_cookies_from_kv()

# الخطوة ب: المرور على الـ 13 قناة وتحديث كوكيز كل قناة على حدة
final_data = {}
print("🚀 بدء عملية التحديث الدوري لجميع القنوات الـ 13...")

for cid, secret_c in CHANNELS_MAP.items():
    last_c = kv_data.get(cid) # جلب الكوكيز الأخير لهذه القناة من الخزنة
    new_c = refresh_channel(cid, secret_c, last_c) # تشغيل دالة التحديث
    if new_c:
        final_data[cid] = new_c # حفظ الكوكيز المحدث في القائمة النهائية

# الخطوة ج: رفع القائمة الكاملة المحدثة إلى Cloudflare KV دفعة واحدة
if final_data:
    res = requests.put(KV_URL, headers=CF_HEADERS, data=json.dumps(final_data))
    if res.status_code == 200:
        print("✅ نجاح عظيم: تم تحديث الخزنة بكوكيز جديد ونشط لكل القنوات الـ 13.")
    else:
        print(f"❌ فشل في رفع البيانات إلى كلاود فلير: {res.text}")
