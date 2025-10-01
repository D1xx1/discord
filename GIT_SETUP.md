# 🚀 Настройка Git для Discord Logger Bot

## Что включено в .gitignore

### ✅ Исключено из Git (не будет коммититься):
- `config.json` - содержит токен бота (конфиденциально!)
- `bot.log` - файлы логов
- `.venv/` - виртуальное окружение Python
- `__pycache__/` - кэш Python
- `.env` - переменные окружения
- Временные файлы и папки IDE

### ✅ Включено в Git (будет коммититься):
- `discord_logger_bot.py` - основной файл бота
- `advanced_logger_bot.py` - расширенная версия
- `start_bot.py` - скрипт запуска
- `requirements.txt` - зависимости
- `config.example.json` - пример конфигурации
- `README.md`, `QUICK_START.md`, `DEPLOYMENT.md` - документация
- `examples.py` - примеры использования
- `.gitignore` - сам файл исключений

## 🛡️ Безопасность

**ВАЖНО!** Файл `config.json` с токеном бота НЕ будет добавлен в Git репозиторий.

Вместо этого используйте `config.example.json` как шаблон.

## 📋 Первоначальная настройка

1. **Скопируйте пример конфигурации:**
   ```bash
   copy config.example.json config.json
   ```

2. **Отредактируйте config.json:**
   - Замените `YOUR_BOT_TOKEN_HERE` на токен вашего бота
   - Установите ID канала для логов

3. **Инициализируйте Git (если нужно):**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Discord Logger Bot"
   ```

## 🔄 Работа с Git

### Добавление файлов:
```bash
git add .                    # Добавить все разрешенные файлы
git add discord_logger_bot.py  # Добавить конкретный файл
```

### Проверка статуса:
```bash
git status                  # Показать статус файлов
git status --ignored        # Показать игнорируемые файлы
```

### Коммит:
```bash
git commit -m "Описание изменений"
```

## ⚠️ Важные моменты

1. **Никогда не коммитьте `config.json`** - он содержит токен бота
2. **Используйте `config.example.json`** как шаблон для других разработчиков
3. **Логи (`bot.log`) не коммитятся** - они генерируются автоматически
4. **Виртуальное окружение (`.venv`) не коммитится** - каждый разработчик создает свое

## 🆘 Если случайно добавили конфиденциальные файлы

```bash
# Удалить из индекса (но оставить файл)
git rm --cached config.json

# Добавить в .gitignore (если еще не добавлен)
echo "config.json" >> .gitignore

# Коммит изменений
git add .gitignore
git commit -m "Remove config.json from tracking"
```

## 📁 Структура проекта

```
discord/
├── .gitignore              # Исключения для Git
├── .venv/                  # Виртуальное окружение (игнорируется)
├── __pycache__/            # Кэш Python (игнорируется)
├── config.json             # Конфигурация с токеном (игнорируется)
├── config.example.json     # Пример конфигурации
├── bot.log                 # Логи (игнорируется)
├── discord_logger_bot.py   # Основной бот
├── advanced_logger_bot.py  # Расширенная версия
├── start_bot.py            # Скрипт запуска
├── requirements.txt        # Зависимости
├── README.md               # Документация
└── ...                     # Другие файлы
```

Теперь ваш проект готов для безопасной работы с Git! 🎉
