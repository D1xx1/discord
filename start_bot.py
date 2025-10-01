#!/usr/bin/env python3
"""
Скрипт для запуска Discord Logger Bot
"""

import os
import sys
import json
import subprocess

def check_requirements():
    """Проверяет установлены ли необходимые пакеты"""
    try:
        import discord
        print("✅ discord.py установлен")
    except ImportError:
        print("❌ discord.py не установлен")
        print("Установите зависимости: pip install -r requirements.txt")
        return False
    return True

def check_config():
    """Проверяет конфигурацию бота"""
    if not os.path.exists('config.json'):
        print("❌ Файл config.json не найден")
        return False
    
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if config.get('token') == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Токен бота не настроен!")
        print("Отредактируйте файл config.json и укажите токен вашего бота")
        return False
    
    if config.get('log_channel_id') == 0:
        print("⚠️  Канал для логов не установлен")
        print("Используйте команду !setlogchannel #канал после запуска бота")
    
    print("✅ Конфигурация проверена")
    return True

def main():
    """Основная функция"""
    print("🤖 Discord Logger Bot - Запуск")
    print("=" * 40)
    
    # Проверяем зависимости
    if not check_requirements():
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    print("\n🚀 Запускаем бота...")
    print("Для остановки нажмите Ctrl+C")
    print("=" * 40)
    
    try:
        # Запускаем бота
        import multi_server_logger_bot
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
