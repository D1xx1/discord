import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os
import re
from typing import Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotConfig:
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        self.log_channel_id = int(os.getenv('LOG_CHANNEL_ID', '0'))
        self.prefix = os.getenv('BOT_PREFIX', '!')
        self.log_messages = os.getenv('LOG_MESSAGES', 'true').lower() == 'true'
        self.log_voice = os.getenv('LOG_VOICE', 'true').lower() == 'true'
        self.log_members = os.getenv('LOG_MEMBERS', 'true').lower() == 'true'
        self.log_channels = os.getenv('LOG_CHANNELS', 'true').lower() == 'true'
        self.log_roles = os.getenv('LOG_ROLES', 'true').lower() == 'true'
        
        # Загружаем конфигурацию из файла
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.token = config.get('token', self.token)
                self.log_channel_id = config.get('log_channel_id', self.log_channel_id)
                self.prefix = config.get('prefix', self.prefix)
                self.log_messages = config.get('log_messages', self.log_messages)
                self.log_voice = config.get('log_voice', self.log_voice)
                self.log_members = config.get('log_members', self.log_members)
                self.log_channels = config.get('log_channels', self.log_channels)
                self.log_roles = config.get('log_roles', self.log_roles)

config = BotConfig()

# Настройка интентов
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.guild_messages = True
intents.dm_messages = True
intents.guild_reactions = True

bot = commands.Bot(command_prefix=config.prefix, intents=intents)

class AdvancedLoggerBot:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = None
        self.message_cache = {}  # Кэш для отслеживания редактирований
        self.rate_limits = {}  # Ограничения на частоту логов
        
    async def get_log_channel(self):
        """Получаем канал для логов"""
        if not self.log_channel and config.log_channel_id:
            try:
                self.log_channel = self.bot.get_channel(config.log_channel_id)
                if not self.log_channel:
                    logger.error(f"Не удалось найти канал с ID {config.log_channel_id}")
            except Exception as e:
                logger.error(f"Ошибка при получении канала логов: {e}")
        return self.log_channel
    
    def is_rate_limited(self, event_type: str, user_id: int) -> bool:
        """Проверяет, не превышен ли лимит частоты для события"""
        now = datetime.utcnow()
        key = f"{event_type}_{user_id}"
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Удаляем старые записи (старше 1 минуты)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if now - timestamp < timedelta(minutes=1)
        ]
        
        # Проверяем лимит (максимум 5 событий в минуту)
        if len(self.rate_limits[key]) >= 5:
            return True
        
        self.rate_limits[key].append(now)
        return False
    
    async def send_log(self, title: str, description: str, color: discord.Color = discord.Color.blue(), 
                      fields: List[tuple] = None, thumbnail: str = None, image: str = None,
                      footer: str = None):
        """Отправляет лог в канал"""
        log_channel = await self.get_log_channel()
        if not log_channel:
            logger.warning("Канал логов не настроен, лог не отправлен")
            return
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        if fields:
            for name, value, inline in fields:
                if len(str(value)) > 1024:  # Ограничение Discord
                    value = str(value)[:1021] + "..."
                embed.add_field(name=name, value=value, inline=inline)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
            
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text=f"ID: {datetime.utcnow().timestamp()}")
            
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Ошибка при отправке лога: {e}")
    
    def format_user_info(self, user: discord.User) -> str:
        """Форматирует информацию о пользователе"""
        return f"{user.mention} (`{user.id}`)\n{user.name}#{user.discriminator}"
    
    def format_channel_info(self, channel: discord.TextChannel) -> str:
        """Форматирует информацию о канале"""
        category = f" в {channel.category.name}" if channel.category else ""
        return f"{channel.mention} (`{channel.id}`){category}"

logger_bot = AdvancedLoggerBot(bot)

@bot.event
async def on_ready():
    """Событие запуска бота"""
    logger.info(f'{bot.user} успешно запущен!')
    logger.info(f'Бот подключен к {len(bot.guilds)} серверам')
    
    # Устанавливаем статус
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="за всеми"
        )
    )

@bot.event
async def on_message(message):
    """Логирование сообщений"""
    if message.author.bot or not config.log_messages:
        return
    
    # Обрабатываем команды
    if message.content.startswith(config.prefix):
        await bot.process_commands(message)
        return
    
    # Логируем обычные сообщения только в текстовых каналах
    if message.guild and isinstance(message.channel, discord.TextChannel):
        # Проверяем лимит частоты
        if logger_bot.is_rate_limited("message", message.author.id):
            return
            
        # Кэшируем сообщение для отслеживания редактирований
        logger_bot.message_cache[message.id] = {
            'content': message.content,
            'author': message.author,
            'timestamp': datetime.utcnow()
        }
        
        # Очищаем старый кэш (старше 1 часа)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        logger_bot.message_cache = {
            msg_id: data for msg_id, data in logger_bot.message_cache.items()
            if data['timestamp'] > cutoff
        }
        
        # Логируем только сообщения с определенными условиями (опционально)
        if len(message.content) > 10 or message.attachments or message.embeds:
            await logger_bot.send_log(
                title="📝 Новое сообщение",
                description=f"**Автор:** {logger_bot.format_user_info(message.author)}\n**Канал:** {logger_bot.format_channel_info(message.channel)}",
                color=discord.Color.green(),
                fields=[
                    ("Содержимое", message.content[:1000] if message.content else "Нет текста", False),
                    ("Вложения", f"{len(message.attachments)} файл(ов)" if message.attachments else "Нет", True),
                    ("Эмбеды", f"{len(message.embeds)} эмбед(ов)" if message.embeds else "Нет", True)
                ],
                thumbnail=message.author.display_avatar.url
            )

@bot.event
async def on_message_delete(message):
    """Логирование удаленных сообщений"""
    if message.author.bot or not config.log_messages:
        return
        
    await logger_bot.send_log(
        title="🗑️ Сообщение удалено",
        description=f"**Автор:** {logger_bot.format_user_info(message.author)}\n**Канал:** {logger_bot.format_channel_info(message.channel)}",
        color=discord.Color.red(),
        fields=[
            ("Содержимое", message.content[:1000] if message.content else "Нет текста", False),
            ("Вложения", f"{len(message.attachments)} файл(ов)" if message.attachments else "Нет", True),
            ("Время создания", message.created_at.strftime('%d.%m.%Y %H:%M:%S'), True)
        ],
        thumbnail=message.author.display_avatar.url
    )

@bot.event
async def on_message_edit(before, after):
    """Логирование отредактированных сообщений"""
    if before.author.bot or before.content == after.content or not config.log_messages:
        return
        
    await logger_bot.send_log(
        title="✏️ Сообщение отредактировано",
        description=f"**Автор:** {logger_bot.format_user_info(before.author)}\n**Канал:** {logger_bot.format_channel_info(before.channel)}",
        color=discord.Color.orange(),
        fields=[
            ("Было", before.content[:1000] if before.content else "Нет текста", False),
            ("Стало", after.content[:1000] if after.content else "Нет текста", False),
            ("Время редактирования", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
        ],
        thumbnail=before.author.display_avatar.url
    )

@bot.event
async def on_reaction_add(reaction, user):
    """Логирование добавления реакций"""
    if user.bot or not config.log_messages:
        return
        
    # Логируем только реакции на сообщения ботов или важные сообщения
    if reaction.message.author.bot or reaction.emoji in ['❤️', '👍', '👎', '🔥', '💯']:
        await logger_bot.send_log(
            title="😀 Реакция добавлена",
            description=f"**Пользователь:** {logger_bot.format_user_info(user)}\n**Канал:** {logger_bot.format_channel_info(reaction.message.channel)}",
            color=discord.Color.yellow(),
            fields=[
                ("Реакция", str(reaction.emoji), True),
                ("Количество", str(reaction.count), True),
                ("Сообщение", reaction.message.content[:200] if reaction.message.content else "Нет текста", False)
            ],
            thumbnail=user.display_avatar.url
        )

@bot.event
async def on_member_join(member):
    """Логирование присоединения участника"""
    if not config.log_members:
        return
        
    # Проверяем, новый ли это аккаунт (младше 7 дней)
    account_age = datetime.utcnow() - member.created_at
    is_new_account = account_age < timedelta(days=7)
    
    await logger_bot.send_log(
        title="👋 Участник присоединился",
        description=f"**Пользователь:** {logger_bot.format_user_info(member)}",
        color=discord.Color.green() if not is_new_account else discord.Color.orange(),
        fields=[
            ("Аккаунт создан", member.created_at.strftime('%d.%m.%Y %H:%M:%S'), True),
            ("Возраст аккаунта", f"{account_age.days} дней", True),
            ("Количество участников", str(member.guild.member_count), True),
            ("Новый аккаунт", "⚠️ Да" if is_new_account else "Нет", True)
        ],
        thumbnail=member.display_avatar.url,
        footer="⚠️ Новый аккаунт" if is_new_account else None
    )

@bot.event
async def on_member_remove(member):
    """Логирование выхода участника"""
    if not config.log_members:
        return
        
    # Вычисляем время на сервере
    time_on_server = "Неизвестно"
    if member.joined_at:
        time_on_server = str(datetime.utcnow() - member.joined_at).split('.')[0]
    
    await logger_bot.send_log(
        title="👋 Участник покинул сервер",
        description=f"**Пользователь:** {logger_bot.format_user_info(member)}",
        color=discord.Color.red(),
        fields=[
            ("Был на сервере с", member.joined_at.strftime('%d.%m.%Y %H:%M:%S') if member.joined_at else "Неизвестно", True),
            ("Время на сервере", time_on_server, True),
            ("Количество участников", str(member.guild.member_count), True)
        ],
        thumbnail=member.display_avatar.url
    )

@bot.event
async def on_member_update(before, after):
    """Логирование изменений участника"""
    if not config.log_members:
        return
        
    changes = []
    
    # Изменение никнейма
    if before.nick != after.nick:
        changes.append(f"**Никнейм:** {before.nick or 'Нет'} → {after.nick or 'Нет'}")
    
    # Изменение ролей
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        
        if added_roles:
            changes.append(f"**Добавлены роли:** {', '.join([role.mention for role in added_roles])}")
        if removed_roles:
            changes.append(f"**Удалены роли:** {', '.join([role.mention for role in removed_roles])}")
    
    # Изменение аватара
    if before.display_avatar.url != after.display_avatar.url:
        changes.append("**Аватар изменен**")
    
    if changes:
        await logger_bot.send_log(
            title="👤 Участник обновлен",
            description=f"**Пользователь:** {logger_bot.format_user_info(after)}\n" + "\n".join(changes),
            color=discord.Color.blue(),
            fields=[
                ("Время изменения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
            ],
            thumbnail=after.display_avatar.url
        )

@bot.event
async def on_guild_channel_create(channel):
    """Логирование создания канала"""
    if not config.log_channels:
        return
        
    await logger_bot.send_log(
        title="📁 Канал создан",
        description=f"**Канал:** {channel.mention} (`{channel.id}`)\n**Тип:** {channel.type.name}",
        color=discord.Color.green(),
        fields=[
            ("Категория", channel.category.name if channel.category else "Нет", True),
            ("Позиция", str(channel.position), True)
        ]
    )

@bot.event
async def on_guild_channel_delete(channel):
    """Логирование удаления канала"""
    if not config.log_channels:
        return
        
    await logger_bot.send_log(
        title="🗑️ Канал удален",
        description=f"**Канал:** #{channel.name} (`{channel.id}`)\n**Тип:** {channel.type.name}",
        color=discord.Color.red(),
        fields=[
            ("Категория", channel.category.name if channel.category else "Нет", True),
            ("Позиция", str(channel.position), True)
        ]
    )

@bot.event
async def on_guild_role_create(role):
    """Логирование создания роли"""
    if not config.log_roles:
        return
        
    await logger_bot.send_log(
        title="🎭 Роль создана",
        description=f"**Роль:** {role.mention} (`{role.id}`)",
        color=discord.Color.green(),
        fields=[
            ("Цвет", str(role.color), True),
            ("Позиция", str(role.position), True),
            ("Разрешения", f"{len([p for p in role.permissions if p[1]])} разрешений", True),
            ("Участников", str(len(role.members)), True)
        ]
    )

@bot.event
async def on_guild_role_delete(role):
    """Логирование удаления роли"""
    if not config.log_roles:
        return
        
    await logger_bot.send_log(
        title="🗑️ Роль удалена",
        description=f"**Роль:** {role.name} (`{role.id}`)",
        color=discord.Color.red(),
        fields=[
            ("Цвет", str(role.color), True),
            ("Позиция", str(role.position), True),
            ("Участников было", str(len(role.members)), True)
        ]
    )

@bot.event
async def on_voice_state_update(member, before, after):
    """Логирование изменений голосового состояния"""
    if not config.log_voice or before.channel == after.channel:
        return
        
    if before.channel is None:
        # Подключился к голосовому каналу
        await logger_bot.send_log(
            title="🎤 Подключился к голосовому каналу",
            description=f"**Пользователь:** {logger_bot.format_user_info(member)}\n**Канал:** {after.channel.mention}",
            color=discord.Color.green(),
            fields=[
                ("Участников в канале", str(len(after.channel.members)), True)
            ],
            thumbnail=member.display_avatar.url
        )
    elif after.channel is None:
        # Отключился от голосового канала
        await logger_bot.send_log(
            title="🎤 Отключился от голосового канала",
            description=f"**Пользователь:** {logger_bot.format_user_info(member)}\n**Канал:** {before.channel.mention}",
            color=discord.Color.red(),
            fields=[
                ("Участников в канале", str(len(before.channel.members)), True)
            ],
            thumbnail=member.display_avatar.url
        )
    else:
        # Перешел в другой голосовой канал
        await logger_bot.send_log(
            title="🎤 Перешел в другой голосовой канал",
            description=f"**Пользователь:** {logger_bot.format_user_info(member)}",
            color=discord.Color.blue(),
            fields=[
                ("Из", before.channel.mention, True),
                ("В", after.channel.mention, True),
                ("Участников в новом канале", str(len(after.channel.members)), True)
            ],
            thumbnail=member.display_avatar.url
        )

# Команды бота
@bot.command(name='setlogchannel')
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    """Устанавливает канал для логов"""
    config.log_channel_id = channel.id
    logger_bot.log_channel = channel
    
    # Сохраняем в файл конфигурации
    config_data = {
        'token': config.token,
        'log_channel_id': config.log_channel_id,
        'prefix': config.prefix,
        'log_messages': config.log_messages,
        'log_voice': config.log_voice,
        'log_members': config.log_members,
        'log_channels': config.log_channels,
        'log_roles': config.log_roles
    }
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    
    await ctx.send(f"✅ Канал для логов установлен: {channel.mention}")

@bot.command(name='togglelogs')
@commands.has_permissions(administrator=True)
async def toggle_logs(ctx, log_type: str):
    """Включает/выключает определенный тип логов"""
    log_type = log_type.lower()
    valid_types = ['messages', 'voice', 'members', 'channels', 'roles']
    
    if log_type not in valid_types:
        await ctx.send(f"❌ Неверный тип логов. Доступные: {', '.join(valid_types)}")
        return
    
    # Переключаем настройку
    setattr(config, f'log_{log_type}', not getattr(config, f'log_{log_type}'))
    
    # Сохраняем в файл
    config_data = {
        'token': config.token,
        'log_channel_id': config.log_channel_id,
        'prefix': config.prefix,
        'log_messages': config.log_messages,
        'log_voice': config.log_voice,
        'log_members': config.log_members,
        'log_channels': config.log_channels,
        'log_roles': config.log_roles
    }
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    
    status = "включены" if getattr(config, f'log_{log_type}') else "выключены"
    await ctx.send(f"✅ Логи типа '{log_type}' {status}")

@bot.command(name='testlog')
@commands.has_permissions(administrator=True)
async def test_log(ctx):
    """Тестирует отправку лога"""
    await logger_bot.send_log(
        title="🧪 Тестовый лог",
        description="Это тестовое сообщение для проверки работы системы логирования",
        color=discord.Color.gold(),
        fields=[
            ("Команда выполнена", ctx.author.mention, True),
            ("Время", datetime.now().strftime('%d.%m.%Y %H:%M:%S'), True),
            ("Сервер", ctx.guild.name, True)
        ],
        footer="Тест системы логирования"
    )
    await ctx.send("✅ Тестовый лог отправлен!")

@bot.command(name='logstatus')
@commands.has_permissions(administrator=True)
async def log_status(ctx):
    """Показывает статус всех типов логов"""
    embed = discord.Embed(
        title="📊 Статус системы логирования",
        color=discord.Color.blue()
    )
    
    status_emoji = {True: "✅", False: "❌"}
    
    embed.add_field(
        name="Типы логов",
        value=f"{status_emoji[config.log_messages]} Сообщения\n"
              f"{status_emoji[config.log_voice]} Голосовая активность\n"
              f"{status_emoji[config.log_members]} Участники\n"
              f"{status_emoji[config.log_channels]} Каналы\n"
              f"{status_emoji[config.log_roles]} Роли",
        inline=True
    )
    
    embed.add_field(
        name="Настройки",
        value=f"**Канал логов:** {f'<#{config.log_channel_id}>' if config.log_channel_id else 'Не установлен'}\n"
              f"**Префикс:** {config.prefix}\n"
              f"**Серверов:** {len(bot.guilds)}",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='botinfo')
async def bot_info(ctx):
    """Информация о боте"""
    embed = discord.Embed(
        title="🤖 Информация о боте",
        color=discord.Color.blue()
    )
    embed.add_field(name="Версия", value="2.0.0", inline=True)
    embed.add_field(name="Серверов", value=len(bot.guilds), inline=True)
    embed.add_field(name="Пользователей", value=len(bot.users), inline=True)
    embed.add_field(name="Канал логов", value=f"<#{config.log_channel_id}>" if config.log_channel_id else "Не установлен", inline=False)
    embed.add_field(name="Префикс", value=config.prefix, inline=True)
    embed.add_field(name="Задержка", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Время работы", value=f"{datetime.utcnow() - bot.start_time if hasattr(bot, 'start_time') else 'Неизвестно'}", inline=True)
    
    await ctx.send(embed=embed)

# Обработка ошибок
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для выполнения этой команды!")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Неверные аргументы команды!")
    else:
        logger.error(f"Ошибка команды {ctx.command}: {error}")
        await ctx.send("❌ Произошла ошибка при выполнении команды!")

if __name__ == "__main__":
    if config.token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Не установлен токен бота!")
        print("Установите переменную окружения DISCORD_BOT_TOKEN или отредактируйте config.json")
        exit(1)
    
    try:
        bot.start_time = datetime.utcnow()
        bot.run(config.token)
    except discord.LoginFailure:
        print("❌ Ошибка: Неверный токен бота!")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
