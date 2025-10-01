# Руководство по развертыванию Discord Logger Bot

## Быстрый старт

### 1. Подготовка

```bash
# Клонируйте или скачайте файлы бота
# Установите Python 3.8+
python --version

# Установите зависимости
pip install -r requirements.txt
```

### 2. Создание бота в Discord

1. Перейдите на https://discord.com/developers/applications
2. Нажмите "New Application"
3. Дайте название вашему боту
4. Перейдите в раздел "Bot"
5. Нажмите "Add Bot"
6. Скопируйте токен бота
7. Включите необходимые интенты:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent (опционально)

### 3. Настройка конфигурации

Отредактируйте файл `config.json`:

```json
{
    "token": "ваш_токен_бота_здесь",
    "log_channel_id": 0,
    "prefix": "!",
    "log_messages": true,
    "log_voice": true,
    "log_members": true,
    "log_channels": true,
    "log_roles": true
}
```

### 4. Приглашение бота на сервер

1. В разделе "OAuth2" > "URL Generator"
2. Выберите "bot" в области Scopes
3. Выберите необходимые разрешения:
   - Read Messages
   - Send Messages
   - Embed Links
   - Read Message History
   - View Channels
   - Manage Roles
   - Connect (для голосовых логов)
   - Speak (для голосовых логов)
4. Скопируйте ссылку и откройте её

### 5. Запуск бота

```bash
# Простой запуск
python discord_logger_bot.py

# Или используйте скрипт запуска
python start_bot.py

# Или расширенную версию
python advanced_logger_bot.py
```

## Настройка канала логов

После запуска бота используйте команду:

```
!setlogchannel #канал-для-логов
```

## Команды бота

| Команда | Описание | Права |
|---------|----------|-------|
| `!setlogchannel #канал` | Установить канал для логов | Администратор |
| `!testlog` | Отправить тестовый лог | Администратор |
| `!togglelogs тип` | Включить/выключить тип логов | Администратор |
| `!logstatus` | Показать статус логов | Администратор |
| `!botinfo` | Информация о боте | Все |

## Типы логов

- `messages` - Сообщения (создание, редактирование, удаление)
- `voice` - Голосовая активность
- `members` - Участники (присоединение, выход, изменения)
- `channels` - Каналы (создание, удаление)
- `roles` - Роли (создание, удаление)

## Развертывание на сервере

### Windows (Service)

1. Установите NSSM (Non-Sucking Service Manager)
2. Создайте сервис:
```cmd
nssm install DiscordLoggerBot "C:\Python\python.exe" "D:\path\to\discord_logger_bot.py"
nssm start DiscordLoggerBot
```

### Linux (Systemd)

Создайте файл `/etc/systemd/system/discord-logger-bot.service`:

```ini
[Unit]
Description=Discord Logger Bot
After=network.target

[Service]
Type=simple
User=discord
WorkingDirectory=/opt/discord-logger-bot
ExecStart=/usr/bin/python3 /opt/discord-logger-bot/discord_logger_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:
```bash
sudo systemctl enable discord-logger-bot
sudo systemctl start discord-logger-bot
```

### Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "discord_logger_bot.py"]
```

Создайте `docker-compose.yml`:

```yaml
version: '3.8'
services:
  discord-logger-bot:
    build: .
    container_name: discord-logger-bot
    restart: unless-stopped
    volumes:
      - ./config.json:/app/config.json
      - ./bot.log:/app/bot.log
    environment:
      - DISCORD_BOT_TOKEN=your_token_here
      - LOG_CHANNEL_ID=1234567890123456789
```

Запустите:
```bash
docker-compose up -d
```

## Мониторинг

### Логи

Бот создает файл `bot.log` с подробными логами.

### Проверка статуса

```bash
# Проверка логов
tail -f bot.log

# Проверка процессов
ps aux | grep python

# Проверка сервиса (Linux)
systemctl status discord-logger-bot
```

## Безопасность

### Рекомендации

1. **Никогда не делитесь токеном бота**
2. **Используйте переменные окружения для продакшена**
3. **Ограничьте права бота только необходимыми**
4. **Регулярно обновляйте зависимости**
5. **Используйте отдельный канал для логов**
6. **Ограничьте доступ к каналу логов**

### Переменные окружения

Создайте файл `.env`:

```env
DISCORD_BOT_TOKEN=your_token_here
LOG_CHANNEL_ID=1234567890123456789
BOT_PREFIX=!
LOG_MESSAGES=true
LOG_VOICE=true
LOG_MEMBERS=true
LOG_CHANNELS=true
LOG_ROLES=true
```

## Устранение неполадок

### Частые проблемы

1. **Бот не запускается**
   - Проверьте токен бота
   - Убедитесь, что Python 3.8+ установлен
   - Проверьте установку зависимостей

2. **Логи не отправляются**
   - Проверьте ID канала логов
   - Убедитесь, что бот имеет права на отправку сообщений
   - Проверьте настройки интентов

3. **Ошибки разрешений**
   - Проверьте права бота на сервере
   - Убедитесь, что бот добавлен на сервер

4. **Высокая нагрузка**
   - Включите фильтрацию сообщений
   - Используйте rate limiting
   - Отключите ненужные типы логов

### Логи ошибок

```bash
# Просмотр логов
grep ERROR bot.log

# Мониторинг в реальном времени
tail -f bot.log | grep ERROR
```

## Обновление

1. Остановите бота
2. Сделайте резервную копию `config.json`
3. Обновите файлы бота
4. Восстановите `config.json`
5. Запустите бота

## Поддержка

При возникновении проблем:

1. Проверьте логи в `bot.log`
2. Убедитесь в правильности конфигурации
3. Проверьте права бота
4. Обратитесь к документации discord.py
