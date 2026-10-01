# مذاكرة Invoice Review Desk

## المشكلة اللي بنحلها

فريق حسابات عايز يراجع بيانات فاتورة والمجموع والتكرار والمبالغ غير المعتادة قبل قرار موظف.

## مسار البيانات

Labelled invoice text → regex أو optional LLM extraction → schema/Decimal validation → missing/reconciliation flags → anomaly screening → duplicate identity → review queue → final human audit.

## ابدئي منين؟

1. شغّلي train وبعده demo واقري الناتج قبل فتح الواجهة.
2. افتحي reports/metrics.json: شوفي اسم البيانات، المقاييس والlimitations.
3. افتحي app.py واتبعي الدوال بالترتيب اللي تحت. بعد كل دالة اسألي: بتاخد إيه؟ بترجع إيه؟ وممكن تفشل إزاي؟
4. جرّبي JSON من samples في الواجهة، وبعدين غيّري input واحد وراقبي النتيجة.
5. افتحي tests: دي حالات سلوك حقيقي، منها inputs غلط وحالات الحدود. شغليها بعد كل تغيير.
6. افتحي notebook في VS Code أو Jupyter مع نفس interpreter بتاع .venv. تثبيت Jupyter اختياري: `python -m pip install notebook`.

## شرح الأجزاء الأساسية

### train

IsolationForest بيتدرّب على log1p(total) وitems من 500 فاتورة synthetic. contamination=.05 بيحدد نسبة تقريبية للشذوذ، مش نسبة احتيال حقيقية.

### money

Decimal عشان .1 + .2 يكون .3؛ بنرفض NaN وInfinity والسالب وأكتر من خانتين عشريتين. ما نعتمدش float لمطابقة مبالغ الفاتورة.

### extract

الوضع المحلي يفهم نص English فيه labels معروفة. مش OCR ومش قراءة PDF. Optional LLM يستخرج بس ومحتاجة مراجعة.

### process

يفحص subtotal + tax = total مع سماح قرش. العملة EGP عشان النموذج التجريبي. الشذوذ يرفع flag فقط، ومفيش auto-approval.

### fingerprint

نفس vendor + invoice number + currency + total يمنع تكرار الفاتورة حتى لو request_id مختلف. ناقص الهوية نستخدم hash النص.

### review

موظف يحدد approved أو rejected مرة واحدة. القرار يتخزن مع reviewer والوقت. مفيش تحويل فلوس، والreviewer اسم محلي مش هوية موثقة.


## API والواجهة

POST يعني إرسال بيانات JSON للخدمة. app.dispatch يحدد الدالة حسب المسار. common.serve بيشغّل HTTP server محلي؛ الواجهة تستدعيه بfetch وترسم نتيجة JSON. مفيش framework مخفي. /health يفحص إن السيرفر موجود، لكنه مش ضمان إن كل model artifact جاهز.

API validation غلط يرجع 400، model لسه متدرّبش يرجع 409، خطأ غير متوقع يرجع 500. في أي مشكلة ابدئي بالtests ثم تأكدي إنك واقفة داخل المجلد الصحيح. لو البورت مستخدم، وقّفي النسخة القديمة بدل تشغيل نسختين.

## تمارين تخلي المشروع بتاعك

1. عدّلي total في المثال وشوفي total_mismatch.
2. ابعتِ نفس الفاتورة بrequest_id جديد وشوفي dedupe.
3. ضيفي line-items وجمع quantity × unit_price مع discounts بدل subtotal جاهز.
4. ضيفي OCR كمرحلة مستقلة، وقيسي جودة الاستخراج قبل anomaly detection.
5. قبل بيانات حقيقية: درّبي على history لعملة واحدة، وضيفي authentication وrole checks للapproval.

## أسئلة تقدري تجاوبيها في مقابلة

- إيه القرار العملي اللي المشروع بيساعد عليه؟
- إيه الجزء machine learning وإيه الجزء rules/automation؟
- إيه مصدر البيانات؟ وهل الأرقام على بيانات حقيقية ولا synthetic؟
- إزاي منعت leakage أو replay أو تكرار الكتابة حسب المشروع؟
- إيه اللي المشروع ما بيقدرش يعمله؟ وإيه خطة قياسه على بيانات واقعية؟
- إيه الإضافة اللي عملتيها بنفسك؟ ورّيني commit أو test يثبتها.

## عرض فيديو 90 ثانية

ابدئي بمشكلة العميل في جملة. اعرضي request ناجح ونتيجته، بعده حالة حدود أو بيانات ناقصة، ثم ملف evaluation أو audit. اختمي بالقيود الحالية وإضافة واحدة نفذتيها. ما تقوليش production-ready أو دقة حقيقية من غير دليل.
