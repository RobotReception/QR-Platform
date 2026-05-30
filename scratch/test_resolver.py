import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from app.services.render_service import _resolve_dynamic_text

# Simulate the context as batch_pipeline would build it
context = {
    "guest": {
        "name": "الشيخ محمد بن عبدالله",
        "name_ar": "الشيخ محمد بن عبدالله",
        "company": "مجموعة الفلاح القابضة",
        "title": "رئيس مجلس الإدارة",
        "custom_fields": {"الجهة": "مجموعة الفلاح القابضة", "المسمى الوظيفي": "رئيس مجلس الإدارة"},
    },
    "event": {"title": "حفل تخرج", "date": "2025-06-28", "time": "19:00"},
    "invite": {"code": "ABC12345", "barcode_payload": "QENTRY-test", "token": "abc123"},
    "custom": {
        "seat": "", "table": "", "gate": "", "hall": "", "zone": "",
        "الجهة": "مجموعة الفلاح القابضة",
        "المسمى الوظيفي": "رئيس مجلس الإدارة",
    },
}

print("=" * 60)
print("TESTING _resolve_dynamic_text()")
print("=" * 60)

test_keys = [
    "اسم الضيف",
    "الاسم",
    "guest.name",
    "name",
    "المسمى الوظيفي",
    "الجهة",
    "guest_name",
    "event.title",
]

for key in test_keys:
    result = _resolve_dynamic_text(key, context)
    status = "OK" if result else "EMPTY!"
    print(f"  data_key='{key}' -> '{result}' [{status}]")
