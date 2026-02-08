# Pivot Screener — Инструкция запуска

## Требования
- Python 3.10+
- Windows PowerShell или командная строка

## Запуск проекта

```powershell
# 1. Перейти в папку проекта
cd A:\Online Screener\V1

# 2. Создать виртуальное окружение
python -m venv venv

# 3. Активировать окружение
.\venv\Scripts\Activate.ps1

# 4. Установить зависимости
pip install fastapi uvicorn jinja2 python-multipart yfinance pandas numpy matplotlib

# 5. Запустить сервер
python run_server.py