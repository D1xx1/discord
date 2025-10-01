import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime
import json
import os

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

# Конфигурация бота
class BotConfig:
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        self.log_channel_id = int(os.getenv('LOG_CHANNEL_ID', '0'))
        self.prefix = os.getenv('BOT_PREFIX', '!')
        
        # Загружаем конфигурацию из файла если существует
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.token = config.get('token', self.token)
                self.log_channel_id = config.get('log_channel_id', self.log_channel_id)
                self.prefix = config.get('prefix', self.prefix)

# Создаем экземпляр конфигурации
config = BotConfig()

# Настройка интентов для получения всех событий
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.guild_messages = True
intents.dm_messages = True

# Создаем бота
bot = commands.Bot(command_prefix=config.prefix, intents=intents)

class LoggerBot:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = None
        
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
    
    async def send_log(self, title, description, color=discord.Color.blue(), fields=None, thumbnail=None):
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
                embed.add_field(name=name, value=value, inline=inline)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Ошибка при отправке лога: {e}")

# Создаем экземпляр логгера
logger_bot = LoggerBot(bot)

@bot.event
async def on_ready():
    """Событие запуска бота"""
    logger.info(f'{bot.user} успешно запущен!')
    logger.info(f'Бот подключен к {len(bot.guilds)} серверам')
    
    # Устанавливаем статус
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="за логами сервера"
        )
    )

@bot.event
async def on_message(message):
    """Логирование сообщений"""
    if message.author.bot:
        return
        
    # Логируем удаление сообщений
    if message.content.startswith(config.prefix):
        await bot.process_commands(message)
        return
    
    # Логируем обычные сообщения (опционально)
    if message.guild:  # Только сообщения на сервере
        await logger_bot.send_log(
            title="📝 Новое сообщение",
            description=f"**Автор:** {message.author.mention}\n**Канал:** {message.channel.mention}\n**Содержимое:** {message.content[:1000]}",
            color=discord.Color.green(),
            fields=[
                ("ID сообщения", str(message.id), True),
                ("ID автора", str(message.author.id), True),
                ("ID канала", str(message.channel.id), True)
            ],
            thumbnail=message.author.display_avatar.url
        )

@bot.event
async def on_message_delete(message):
    """Логирование удаленных сообщений"""
    if message.author.bot:
        return
        
    await logger_bot.send_log(
        title="🗑️ Сообщение удалено",
        description=f"**Автор:** {message.author.mention}\n**Канал:** {message.channel.mention}\n**Содержимое:** {message.content[:1000] if message.content else 'Нет текста'}",
        color=discord.Color.red(),
        fields=[
            ("ID сообщения", str(message.id), True),
            ("ID автора", str(message.author.id), True),
            ("ID канала", str(message.channel.id), True)
        ],
        thumbnail=message.author.display_avatar.url
    )

@bot.event
async def on_message_edit(before, after):
    """Логирование отредактированных сообщений"""
    if before.author.bot or before.content == after.content:
        return
        
    await logger_bot.send_log(
        title="✏️ Сообщение отредактировано",
        description=f"**Автор:** {before.author.mention}\n**Канал:** {before.channel.mention}",
        color=discord.Color.orange(),
        fields=[
            ("Было", before.content[:1000] if before.content else "Нет текста", False),
            ("Стало", after.content[:1000] if after.content else "Нет текста", False),
            ("ID сообщения", str(before.id), True),
            ("ID автора", str(before.author.id), True)
        ],
        thumbnail=before.author.display_avatar.url
    )

@bot.event
async def on_member_join(member):
    """Логирование присоединения участника"""
    await logger_bot.send_log(
        title="👋 Участник присоединился",
        description=f"**Пользователь:** {member.mention}\n**Аккаунт создан:** {member.created_at.strftime('%d.%m.%Y %H:%M:%S')}",
        color=discord.Color.green(),
        fields=[
            ("ID пользователя", str(member.id), True),
            ("Количество участников", str(member.guild.member_count), True)
        ],
        thumbnail=member.display_avatar.url
    )

@bot.event
async def on_member_remove(member):
    """Логирование выхода участника"""
    await logger_bot.send_log(
        title="👋 Участник покинул сервер",
        description=f"**Пользователь:** {member.mention}\n**Был на сервере с:** {member.joined_at.strftime('%d.%m.%Y %H:%M:%S') if member.joined_at else 'Неизвестно'}",
        color=discord.Color.red(),
        fields=[
            ("ID пользователя", str(member.id), True),
            ("Количество участников", str(member.guild.member_count), True)
        ],
        thumbnail=member.display_avatar.url
    )

@bot.event
async def on_member_update(before, after):
    """Логирование изменений участника"""
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
    
    if changes:
        await logger_bot.send_log(
            title="👤 Участник обновлен",
            description=f"**Пользователь:** {after.mention}\n" + "\n".join(changes),
            color=discord.Color.blue(),
            fields=[
                ("ID пользователя", str(after.id), True)
            ],
            thumbnail=after.display_avatar.url
        )

@bot.event
async def on_guild_channel_create(channel):
    """Логирование создания канала"""
    await logger_bot.send_log(
        title="📁 Канал создан",
        description=f"**Канал:** {channel.mention}\n**Тип:** {channel.type.name}",
        color=discord.Color.green(),
        fields=[
            ("ID канала", str(channel.id), True),
            ("Категория", channel.category.name if channel.category else "Нет", True)
        ]
    )

@bot.event
async def on_guild_channel_delete(channel):
    """Логирование удаления канала"""
    await logger_bot.send_log(
        title="🗑️ Канал удален",
        description=f"**Канал:** #{channel.name}\n**Тип:** {channel.type.name}",
        color=discord.Color.red(),
        fields=[
            ("ID канала", str(channel.id), True),
            ("Категория", channel.category.name if channel.category else "Нет", True)
        ]
    )

@bot.event
async def on_guild_role_create(role):
    """Логирование создания роли"""
    await logger_bot.send_log(
        title="🎭 Роль создана",
        description=f"**Роль:** {role.mention}\n**Цвет:** {role.color}",
        color=discord.Color.green(),
        fields=[
            ("ID роли", str(role.id), True),
            ("Позиция", str(role.position), True),
            ("Разрешения", str(role.permissions.value), False)
        ]
    )

@bot.event
async def on_guild_role_delete(role):
    """Логирование удаления роли"""
    await logger_bot.send_log(
        title="🗑️ Роль удалена",
        description=f"**Роль:** {role.name}",
        color=discord.Color.red(),
        fields=[
            ("ID роли", str(role.id), True),
            ("Позиция", str(role.position), True)
        ]
    )

@bot.event
async def on_voice_state_update(member, before, after):
    """Логирование изменений голосового состояния"""
    if before.channel != after.channel:
        if before.channel is None:
            # Подключился к голосовому каналу
            await logger_bot.send_log(
                title="🎤 Подключился к голосовому каналу",
                description=f"**Пользователь:** {member.mention}\n**Канал:** {after.channel.mention}",
                color=discord.Color.green(),
                fields=[
                    ("ID пользователя", str(member.id), True),
                    ("ID канала", str(after.channel.id), True)
                ],
                thumbnail=member.display_avatar.url
            )
        elif after.channel is None:
            # Отключился от голосового канала
            await logger_bot.send_log(
                title="🎤 Отключился от голосового канала",
                description=f"**Пользователь:** {member.mention}\n**Канал:** {before.channel.mention}",
                color=discord.Color.red(),
                fields=[
                    ("ID пользователя", str(member.id), True),
                    ("ID канала", str(before.channel.id), True)
                ],
                thumbnail=member.display_avatar.url
            )
        else:
            # Перешел в другой голосовой канал
            await logger_bot.send_log(
                title="🎤 Перешел в другой голосовой канал",
                description=f"**Пользователь:** {member.mention}\n**Из:** {before.channel.mention}\n**В:** {after.channel.mention}",
                color=discord.Color.blue(),
                fields=[
                    ("ID пользователя", str(member.id), True)
                ],
                thumbnail=member.display_avatar.url
            )

# Команды бота
@bot.command(name='setlogchannel')
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    """Устанавливает канал для логов"""
    config.log_channel_id = channel.id
    
    # Сохраняем в файл конфигурации
    config_data = {
        'token': config.token,
        'log_channel_id': config.log_channel_id,
        'prefix': config.prefix
    }
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    
    logger_bot.log_channel = channel
    await ctx.send(f"✅ Канал для логов установлен: {channel.mention}")

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
            ("Время", datetime.now().strftime('%d.%m.%Y %H:%M:%S'), True)
        ]
    )
    await ctx.send("✅ Тестовый лог отправлен!")

@bot.command(name='botinfo')
async def bot_info(ctx):
    """Информация о боте"""
    embed = discord.Embed(
        title="🤖 Информация о боте",
        color=discord.Color.blue()
    )
    embed.add_field(name="Версия", value="1.0.0", inline=True)
    embed.add_field(name="Серверов", value=len(bot.guilds), inline=True)
    embed.add_field(name="Пользователей", value=len(bot.users), inline=True)
    embed.add_field(name="Канал логов", value=f"<#{config.log_channel_id}>" if config.log_channel_id else "Не установлен", inline=False)
    embed.add_field(name="Префикс", value=config.prefix, inline=True)
    embed.add_field(name="Задержка", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    await ctx.send(embed=embed)

# Обработка ошибок
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для выполнения этой команды!")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Игнорируем неизвестные команды
    else:
        logger.error(f"Ошибка команды {ctx.command}: {error}")
        await ctx.send("❌ Произошла ошибка при выполнении команды!")

if __name__ == "__main__":
    if config.token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Не установлен токен бота!")
        print("Установите переменную окружения DISCORD_BOT_TOKEN или отредактируйте config.json")
        exit(1)
    
    try:
        bot.run(config.token)
    except discord.LoginFailure:
        print("❌ Ошибка: Неверный токен бота!")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
