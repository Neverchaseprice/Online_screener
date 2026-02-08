#!/usr/bin/env python3
"""
Запуск сервера Pivot Screener
Поддерживает:
  - Автоперезагрузку в режиме разработки
  - Продакшн-режим без автоперезагрузки
  - Проверку зависимостей
  - Корректное завершение работы
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path

def check_dependencies():
    """Проверка наличия всех необходимых зависимостей"""
    required_packages = [
        'fastapi', 'uvicorn', 'jinja2', 'yfinance', 
        'pandas', 'numpy', 'matplotlib'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Отсутствуют необходимые пакеты:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nУстановите зависимости командой:")
        print("   pip install -r requirements.txt")
        return False
    return True

def create_directories():
    """Создание необходимых директорий если их нет"""
    dirs = [
        Path("app/templates"),
        Path("app/static"),
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"✓ Директория: {d} (создана/проверена)")

def main():
    parser = argparse.ArgumentParser(description='Pivot Screener Server')
    parser.add_argument('--host', default='0.0.0.0', help='Хост для запуска (по умолчанию: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Порт (по умолчанию: 8000)')
    parser.add_argument('--reload', action='store_true', help='Автоперезагрузка при изменении кода')
    parser.add_argument('--prod', action='store_true', help='Продакшн-режим (без автоперезагрузки, больше воркеров)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🚀 ЗАПУСК PIVOT SCREENER")
    print("=" * 70)
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Создание директорий
    create_directories()
    
    # Настройки запуска
    if args.prod:
        print("\n🔧 Режим: ПРОДАКШН")
        reload = False
        workers = 4
        log_level = "info"
    else:
        print("\n🔧 Режим: РАЗРАБОТКА")
        reload = args.reload or True
        workers = 1
        log_level = "debug"
    
    print(f"   Host:      {args.host}")
    print(f"   Port:      {args.port}")
    print(f"   Reload:    {reload}")
    print(f"   Workers:   {workers}")
    print(f"   Log level: {log_level}")
    print("=" * 70)
    print(f"\n🌍 Откройте в браузере: http://localhost:{args.port}")
    print("\n💡 Горячие клавиши:")
    print("   Ctrl+C - остановить сервер")
    print("   Ctrl+Enter на странице - перегенерировать графики")
    print("   Esc на странице - снять все чекбоксы")
    print("=" * 70)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=reload,
            workers=workers,
            log_level=log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Сервер остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка при запуске сервера: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()