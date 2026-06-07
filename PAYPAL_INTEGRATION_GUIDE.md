# دليل تكامل PayPal مع منصة QR

تم بنجاح تنفيذ تكامل PayPal كامل مع منصة QR لاستبدال Stripe في معالجة الاشتراكات والدفعات.

## الملفات المضافة/المعدلة

### Backend (Python/FastAPI)

1. **requirements.txt**
   - إضافة `paypalrestsdk==1.13.3`

2. **app/config.py**
   - إعدادات PayPal موجودة بالفعل:
     - `PAYPAL_CLIENT_ID`
     - `PAYPAL_CLIENT_SECRET`
     - `PAYPAL_MODE` (sandbox/live)

3. **app/services/paypal_service.py** (جديد)
   - خدمة PayPal لإدارة الاتصال بـ PayPal API
   - دوال:
     - `create_billing_plan()` - إنشاء خطة اشتراك
     - `create_subscription()` - إنشاء اتفاقية اشتراك
     - `execute_subscription()` - تنفيذ الاشتراك بعد الموافقة
     - `cancel_subscription()` - إلغاء اشتراك
     - `get_subscription_details()` - الحصول على تفاصيل اشتراك
     - `verify_webhook_signature()` - التحقق من توقيع webhook

4. **app/models/subscription.py**
   - إضافة `PaymentProvider` enum (stripe, paypal, mock_bypass)
   - تحديث `SubscriptionRead.provider` لاستخدام `PaymentProvider`

5. **app/routes/subscriptions.py**
   - تحديث endpoint `/subscriptions/checkout` لاستخدام PayPal
   - إضافة endpoint `/subscriptions/paypal/execute` لتنفيذ الاشتراك
   - تحديث endpoint `/subscriptions/cancel` لدعم PayPal
   - إضافة endpoint `/webhooks/paypal` لاستقبال إشعارات PayPal
   - الاحتفاظ بـ Stripe webhooks للتوافق العكسي

6. **supabase/migration_v16_paypal_pending_subscriptions.sql** (جديد)
   - إنشاء جدول `pending_subscriptions` لتخزين الاشتراكات المؤقتة قبل الموافقة

7. **run_migration_v16.py** (جديد)
   - سكريبت لتنفيذ migration v16

### Frontend (React/TypeScript)

8. **frontend/src/features/settings/api/subscriptionsApi.ts**
   - تحديث `createCheckoutSession()` لقبول `paymentProvider` parameter
   - إضافة `executePayPalSubscription()` لتنفيذ الاشتراك
   - إضافة `cancelSubscription()` لإلغاء الاشتراك

9. **frontend/src/features/dashboard/components/PricingModal.tsx**
   - تحديث لاستخدام PayPal بدلاً من Stripe
   - تمرير `paymentProvider='paypal'` إلى API

10. **frontend/src/features/settings/pages/PayPalExecutePage.tsx** (جديد)
    - صفحة لمعالجة رد PayPal بعد الموافقة
    - تنفيذ الاشتراك وتوجيه المستخدم إلى لوحة التحكم

11. **frontend/src/app/router/index.tsx**
    - إضافة `PayPalExecutePage` إلى router
    - إضافة route `/billing/paypal/execute`

## خطوات التثبيت والإعداد

### 1. إعداد PayPal Developer Account

1. قم بإنشاء حساب على [PayPal Developer](https://developer.paypal.com/dashboard/)
2. أنشئ تطبيق جديد (App)
3. احصل على:
   - Client ID
   - Client Secret
4. تأكد من تفعيل:
   - Billing Plans API
   - Subscriptions API
   - Webhooks

### 2. تحديث ملف .env

```bash
# PayPal
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYPAL_MODE=sandbox  # استخدم 'live' للإنتاج
```

### 3. تنفيذ Migration SQL

```bash
# تأكد من تشغيل Supabase محلياً
cd d:\QR
python run_migration_v16.py
```

أو تنفيذ يدوياً عبر Supabase Dashboard:
```sql
-- افتح ملف supabase/migration_v16_paypal_pending_subscriptions.sql
-- نفذ الأوامر في SQL Editor
```

### 4. تثبيت المكتبات

```bash
pip install paypalrestsdk
```

أو من requirements.txt:
```bash
pip install -r requirements.txt
```

### 5. إعداد Webhooks PayPal

1. في PayPal Developer Dashboard، أضف webhook:
   - URL: `https://your-domain.com/webhooks/paypal`
   - Events:
     - `BILLING.SUBSCRIPTION.ACTIVATED`
     - `BILLING.SUBSCRIPTION.CANCELLED`
     - `PAYMENT.SALE.COMPLETED`
     - `PAYMENT.SALE.REFUNDED`

## سير العمل (Workflow)

### عملية الاشتراك الجديد

1. **المستخدم يختار باقة** في PricingModal
2. **Frontend** يستدعي `createCheckoutSession(planCode, 'paypal')`
3. **Backend**:
   - ينشئ PayPal Billing Plan
   - ينشئ PayPal Subscription Agreement
   - يخزن الاشتراك في `pending_subscriptions`
   - يرجع `approval_url` للمستخدم
4. **Frontend** يوجه المستخدم إلى PayPal
5. **المستخدم** يوافق على الدفع في PayPal
6. **PayPal** يعيد المستخدم إلى `/billing/paypal/execute?token=...`
7. **PayPalExecutePage**:
   - يستخرج token من URL
   - يستدعي `executePayPalSubscription(token)`
8. **Backend**:
   - ينفذ الاشتراك عبر PayPal API
   - ينشئ اشتراك في قاعدة البيانات
   - يحذف من `pending_subscriptions`
   - يرجع نجاح
9. **Frontend** يوجه المستخدم إلى Dashboard

### إلغاء الاشتراك

1. المستخدم يضغط "إلغاء"
2. Frontend يستدعي `cancelSubscription()`
3. Backend:
   - يتحقق من provider (paypal/stripe)
   - يلغي الاشتراك عبر PayPal API
   - يحدث حالة الاشتراك في قاعدة البيانات

### Webhooks

PayPal يرسل إشعارات إلى `/webhooks/paypal`:
- `BILLING.SUBSCRIPTION.ACTIVATED` - تفعيل اشتراك
- `BILLING.SUBSCRIPTION.CANCELLED` - إلغاء اشتراك
- `PAYMENT.SALE.COMPLETED` - دفع ناجح
- `PAYMENT.SALE.REFUNDED` - استرداد

## الميزات المدعومة

- ✅ إنشاء اشتراكات جديدة
- ✅ تنفيذ الاشتراك بعد الموافقة
- ✅ إلغاء الاشتراكات
- ✅ Webhooks لمزامنة الحالة
- ✅ دعم الباقات المخصصة (Custom Plans)
- ✅ دعم Sandbox و Live
- ✅ الاحتفاظ بـ Stripe للتوافق العكسي
- ✅ Mock bypass للتطوير المحلي

## ملاحظات مهمة

1. **PayPal Plans**: يتم إنشاء PayPal Billing Plans ديناميكياً. في الإنتاج، يُفضل تخزينها وتخزين IDs لتجنب الإنشاء المتكرر.

2. **Webhook Signature**: التحقق من التوقيع غير مكتمل بالكامل حالياً. في الإنتاج، يجب تطبيق التحقق الأمني الكامل.

3. **Currency**: النظام يستخدم SAR (ريال سعودي). تأكد من تفعيل هذا العملة في PayPal.

4. **Migration**: إذا فشل تنفيذ migration تلقائياً، نفذ SQL يدوياً عبر Supabase Dashboard.

5. **Testing**: استخدم PayPal Sandbox للاختبار قبل الانتقال إلى Live.

## استكشاف الأخطاء

### PayPal غير مُكوّن

إذا ظهر خطأ "PayPal not configured":
- تأكد من تعبئة `PAYPAL_CLIENT_ID` و `PAYPAL_CLIENT_SECRET` في .env
- تأكد من أن القيم ليست القيم الافتراضية

### فشل إنشاء Billing Plan

- تأكد من تفعيل Billing Plans API في PayPal Developer Dashboard
- تأكد من صحة العملة (SAR)

### فشل تنفيذ الاشتراك

- تأكد من أن token صحيح
- تحقق من logs في Backend
- تأكد من أن جدول `pending_subscriptions` موجود

### Webhook لا يعمل

- تأكد من أن URL صحيح ومتاح للإنترنت
- تأكد من تفعيل Webhook في PayPal Dashboard
- تحقق من أن events المطلوبة مفعلة

## الدعم

للمساعدة أو الاستفسارات:
- راجع ملفات الكود المذكورة أعلاه
- تحقق من logs في Backend
- راجع PayPal Developer Documentation
