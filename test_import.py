# test_import.py
print("1. Пытаемся импортировать utils...")
try:
    from app import utils
    print("✅ Успешно импортировано")
    print("2. Проверяем наличие plt...")
    import matplotlib.pyplot as plt
    print(f"✅ plt доступен: {plt}")
except Exception as e:
    print(f"❌ Ошибка при импорте: {e}")
    import traceback
    traceback.print_exc()