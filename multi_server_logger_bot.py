import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os
import re
from typing import Optional, List, Dict

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

class MultiServerConfig:
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        self.prefix = os.getenv('BOT_PREFIX', '!')
        self.log_messages = os.getenv('LOG_MESSAGES', 'true').lower() == 'true'
        self.log_voice = os.getenv('LOG_VOICE', 'true').lower() == 'true'
        self.log_members = os.getenv('LOG_MEMBERS', 'true').lower() == 'true'
        self.log_channels = os.getenv('LOG_CHANNELS', 'true').lower() == 'true'
        self.log_roles = os.getenv('LOG_ROLES', 'true').lower() == 'true'
        
        # Словарь для хранения каналов логов для каждого сервера
        self.server_log_channels = {}  # {guild_id: channel_id}
        
        # Загружаем конфигурацию из файла
        if os.path.exists('multi_server_config.json'):
            with open('multi_server_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.token = config.get('token', self.token)
                self.prefix = config.get('prefix', self.prefix)
                self.log_messages = config.get('log_messages', self.log_messages)
                self.log_voice = config.get('log_voice', self.log_voice)
                self.log_members = config.get('log_members', self.log_members)
                self.log_channels = config.get('log_channels', self.log_channels)
                self.log_roles = config.get('log_roles', self.log_roles)
                self.server_log_channels = config.get('server_log_channels', {})
    
    def get_log_channel_id(self, guild_id: int) -> Optional[int]:
        """Получает ID канала логов для конкретного сервера"""
        return self.server_log_channels.get(str(guild_id))
    
    def set_log_channel_id(self, guild_id: int, channel_id: int):
        """Устанавливает ID канала логов для конкретного сервера"""
        self.server_log_channels[str(guild_id)] = channel_id
        self.save_config()
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        config_data = {
            'token': self.token,
            'prefix': self.prefix,
            'log_messages': self.log_messages,
            'log_voice': self.log_voice,
            'log_members': self.log_members,
            'log_channels': self.log_channels,
            'log_roles': self.log_roles,
            'server_log_channels': self.server_log_channels
        }
        
        with open('multi_server_config.json', 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)

config = MultiServerConfig()

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

class MultiServerLoggerBot:
    def __init__(self, bot):
        self.bot = bot
        self.rate_limits = {}  # Ограничения на частоту логов
        
    async def get_log_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Получает канал для логов конкретного сервера"""
        channel_id = config.get_log_channel_id(guild_id)
        if not channel_id:
            return None
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Не удалось найти канал с ID {channel_id} для сервера {guild_id}")
            return channel
        except Exception as e:
            logger.error(f"Ошибка при получении канала логов для сервера {guild_id}: {e}")
            return None
    
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
    
    async def send_log(self, guild_id: int, title: str, description: str, 
                      color: discord.Color = discord.Color.blue(), 
                      fields: List[tuple] = None, thumbnail: str = None, 
                      image: str = None, footer: str = None):
        """Отправляет лог в канал конкретного сервера"""
        log_channel = await self.get_log_channel(guild_id)
        if not log_channel:
            logger.warning(f"Канал логов не настроен для сервера {guild_id}, лог не отправлен")
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
            embed.set_footer(text=f"Сервер: {guild_id} | ID: {datetime.utcnow().timestamp()}")
            
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Ошибка при отправке лога на сервер {guild_id}: {e}")
    
    def format_user_info(self, user: discord.User) -> str:
        """Форматирует информацию о пользователе"""
        return f"{user.mention} (`{user.id}`)\n{user.name}#{user.discriminator}"
    
    def format_channel_info(self, channel: discord.TextChannel) -> str:
        """Форматирует информацию о канале"""
        category = f" в {channel.category.name}" if channel.category else ""
        return f"{channel.mention} (`{channel.id}`){category}"

logger_bot = MultiServerLoggerBot(bot)

@bot.event
async def on_ready():
    """Событие запуска бота"""
    logger.info(f'{bot.user} успешно запущен!')
    logger.info(f'Бот подключен к {len(bot.guilds)} серверам')
    
    # Показываем информацию о настроенных каналах логов
    for guild in bot.guilds:
        channel_id = config.get_log_channel_id(guild.id)
        if channel_id:
            channel = bot.get_channel(channel_id)
            channel_name = channel.name if channel else "Не найден"
            logger.info(f"Сервер {guild.name}: канал логов #{channel_name}")
        else:
            logger.info(f"Сервер {guild.name}: канал логов не настроен")
    
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
    
    # Логируем только в текстовых каналах на серверах
    if message.guild and isinstance(message.channel, discord.TextChannel):
        # Проверяем лимит частоты
        if logger_bot.is_rate_limited("message", message.author.id):
            return
            
        # Логируем только важные сообщения
        if len(message.content) > 10 or message.attachments or message.embeds:
            await logger_bot.send_log(
                guild_id=message.guild.id,
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
    if message.author.bot or not config.log_messages or not message.guild:
        return
        
    await logger_bot.send_log(
        guild_id=message.guild.id,
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
    if before.author.bot or before.content == after.content or not config.log_messages or not before.guild:
        return
        
    await logger_bot.send_log(
        guild_id=before.guild.id,
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
async def on_member_join(member):
    """Логирование присоединения участника"""
    if not config.log_members or not member.guild:
        return
        
    # Проверяем, новый ли это аккаунт (младше 7 дней)
    account_age = datetime.utcnow() - member.created_at
    is_new_account = account_age < timedelta(days=7)
    
    await logger_bot.send_log(
        guild_id=member.guild.id,
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
    if not config.log_members or not member.guild:
        return
        
    # Вычисляем время на сервере
    time_on_server = "Неизвестно"
    if member.joined_at:
        time_on_server = str(datetime.utcnow() - member.joined_at).split('.')[0]
    
    await logger_bot.send_log(
        guild_id=member.guild.id,
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
    if not config.log_members or not after.guild:
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
            guild_id=after.guild.id,
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
    if not config.log_channels or not channel.guild:
        return
        
    await logger_bot.send_log(
        guild_id=channel.guild.id,
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
    if not config.log_channels or not channel.guild:
        return
        
    await logger_bot.send_log(
        guild_id=channel.guild.id,
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
    if not config.log_roles or not role.guild:
        return
        
    await logger_bot.send_log(
        guild_id=role.guild.id,
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
    if not config.log_roles or not role.guild:
        return
        
    await logger_bot.send_log(
        guild_id=role.guild.id,
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
    if not config.log_voice or before.channel == after.channel or not member.guild:
        return
        
    if before.channel is None:
        # Подключился к голосовому каналу
        await logger_bot.send_log(
            guild_id=member.guild.id,
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
            guild_id=member.guild.id,
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
            guild_id=member.guild.id,
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

@bot.event
async def on_voice_client_disconnect(voice_client):
    """Логирование отключения бота от голосового канала"""
    if not voice_client.guild:
        return
        
    await logger_bot.send_log(
        guild_id=voice_client.guild.id,
        title="🎤 Бот отключен от голосового канала",
        description=f"**Канал:** {voice_client.channel.mention if voice_client.channel else 'Неизвестно'}\n**Причина:** Автоматическое отключение",
        color=discord.Color.orange(),
        fields=[
            ("Время отключения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
        ]
    )

# Команды бота
@bot.command(name='setlogchannel')
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    """Устанавливает канал для логов на текущем сервере"""
    config.set_log_channel_id(ctx.guild.id, channel.id)
    
    await ctx.send(f"✅ Канал для логов установлен: {channel.mention}\n"
                  f"Теперь все логи сервера **{ctx.guild.name}** будут отправляться в этот канал!")

@bot.command(name='removelogchannel')
@commands.has_permissions(administrator=True)
async def remove_log_channel(ctx):
    """Удаляет настройку канала логов для текущего сервера"""
    if str(ctx.guild.id) in config.server_log_channels:
        del config.server_log_channels[str(ctx.guild.id)]
        config.save_config()
        await ctx.send(f"✅ Канал логов удален для сервера **{ctx.guild.name}**")
    else:
        await ctx.send(f"❌ Канал логов не был настроен для сервера **{ctx.guild.name}**")

@bot.command(name='togglelogs')
@commands.has_permissions(administrator=True)
async def toggle_logs(ctx, log_type: str):
    """Включает/выключает определенный тип логов (глобально)"""
    log_type = log_type.lower()
    valid_types = ['messages', 'voice', 'members', 'channels', 'roles']
    
    if log_type not in valid_types:
        await ctx.send(f"❌ Неверный тип логов. Доступные: {', '.join(valid_types)}")
        return
    
    # Переключаем настройку
    setattr(config, f'log_{log_type}', not getattr(config, f'log_{log_type}'))
    config.save_config()
    
    status = "включены" if getattr(config, f'log_{log_type}') else "выключены"
    await ctx.send(f"✅ Логи типа '{log_type}' {status} для всех серверов")

@bot.command(name='testlog')
@commands.has_permissions(administrator=True)
async def test_log(ctx):
    """Тестирует отправку лога на текущем сервере"""
    await logger_bot.send_log(
        guild_id=ctx.guild.id,
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
    """Показывает статус логов для текущего сервера"""
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
    
    channel_id = config.get_log_channel_id(ctx.guild.id)
    channel_info = f"<#{channel_id}>" if channel_id else "Не установлен"
    
    embed.add_field(
        name="Настройки сервера",
        value=f"**Канал логов:** {channel_info}\n"
              f"**Префикс:** {config.prefix}\n"
              f"**Серверов:** {len(bot.guilds)}",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='serverlist')
@commands.has_permissions(administrator=True)
async def server_list(ctx):
    """Показывает список всех серверов и их каналов логов"""
    embed = discord.Embed(
        title="🌐 Список серверов",
        description=f"Бот подключен к {len(bot.guilds)} серверам",
        color=discord.Color.blue()
    )
    
    for guild in bot.guilds:
        channel_id = config.get_log_channel_id(guild.id)
        if channel_id:
            channel = bot.get_channel(channel_id)
            channel_name = f"#{channel.name}" if channel else "Канал не найден"
            status = "✅"
        else:
            channel_name = "Не настроен"
            status = "❌"
        
        embed.add_field(
            name=f"{status} {guild.name}",
            value=f"**Канал логов:** {channel_name}\n**Участников:** {guild.member_count}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='joinvoice')
@commands.has_permissions(administrator=True)
async def join_voice(ctx, *, channel: discord.VoiceChannel = None):
    """Подключает бота к голосовому каналу"""
    if not channel:
        # Если канал не указан, пытаемся подключиться к каналу автора команды
        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
        else:
            await ctx.send("❌ Укажите голосовой канал или подключитесь к голосовому каналу!")
            return
    
    try:
        # Проверяем, подключен ли уже бот к голосовому каналу на этом сервере
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
        
        # Подключаемся к каналу
        voice_client = await channel.connect()
        
        await logger_bot.send_log(
            guild_id=ctx.guild.id,
            title="🎤 Бот подключен к голосовому каналу",
            description=f"**Канал:** {channel.mention}\n**Подключил:** {ctx.author.mention}",
            color=discord.Color.green(),
            fields=[
                ("Участников в канале", str(len(channel.members)), True),
                ("Время подключения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
            ]
        )
        
        await ctx.send(f"✅ Бот подключен к голосовому каналу {channel.mention}!")
        
    except Exception as e:
        await ctx.send(f"❌ Ошибка подключения к голосовому каналу: {e}")
        logger.error(f"Ошибка подключения к голосовому каналу: {e}")

@bot.command(name='leavevoice')
@commands.has_permissions(administrator=True)
async def leave_voice(ctx):
    """Отключает бота от голосового канала"""
    if not ctx.guild.voice_client:
        await ctx.send("❌ Бот не подключен к голосовому каналу!")
        return
    
    try:
        channel = ctx.guild.voice_client.channel
        await ctx.guild.voice_client.disconnect()
        
        await logger_bot.send_log(
            guild_id=ctx.guild.id,
            title="🎤 Бот отключен от голосового канала",
            description=f"**Канал:** {channel.mention}\n**Отключил:** {ctx.author.mention}",
            color=discord.Color.red(),
            fields=[
                ("Время отключения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
            ]
        )
        
        await ctx.send("✅ Бот отключен от голосового канала!")
        
    except Exception as e:
        await ctx.send(f"❌ Ошибка отключения от голосового канала: {e}")
        logger.error(f"Ошибка отключения от голосового канала: {e}")

@bot.command(name='voiceinfo')
@commands.has_permissions(administrator=True)
async def voice_info(ctx):
    """Показывает информацию о голосовом подключении"""
    if not ctx.guild.voice_client:
        await ctx.send("❌ Бот не подключен к голосовому каналу!")
        return
    
    voice_client = ctx.guild.voice_client
    channel = voice_client.channel
    
    embed = discord.Embed(
        title="🎤 Информация о голосовом подключении",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Канал", value=channel.mention, inline=True)
    embed.add_field(name="Статус", value="Подключен", inline=True)
    embed.add_field(name="Участников", value=str(len(channel.members)), inline=True)
    
    embed.add_field(name="Задержка", value=f"{round(voice_client.latency * 1000)}ms", inline=True)
    embed.add_field(name="Громкость", value=f"{voice_client.source.volume * 100:.0f}%" if voice_client.source else "Не установлено", inline=True)
    embed.add_field(name="Время подключения", value=datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='voiceactivity')
@commands.has_permissions(administrator=True)
async def voice_activity(ctx):
    """Показывает активность во всех голосовых каналах сервера"""
    voice_channels = [ch for ch in ctx.guild.voice_channels if len(ch.members) > 0]
    
    if not voice_channels:
        await ctx.send("❌ В голосовых каналах нет участников!")
        return
    
    embed = discord.Embed(
        title="🎤 Активность голосовых каналов",
        description=f"**Сервер:** {ctx.guild.name}",
        color=discord.Color.blue()
    )
    
    for channel in voice_channels:
        members_list = []
        for member in channel.members:
            status_emoji = "🔊" if not member.voice.mute else "🔇"
            if member.voice.self_mute:
                status_emoji = "🔇"
            if member.voice.self_deaf:
                status_emoji = "🔇"
            if member.voice.afk:
                status_emoji = "😴"
            
            members_list.append(f"{status_emoji} {member.display_name}")
        
        embed.add_field(
            name=f"🔊 {channel.name} ({len(channel.members)} участников)",
            value="\n".join(members_list[:10]) + ("..." if len(members_list) > 10 else ""),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='botinfo')
async def bot_info(ctx):
    """Информация о боте"""
    embed = discord.Embed(
        title="🤖 Информация о боте",
        color=discord.Color.blue()
    )
    embed.add_field(name="Версия", value="3.1.0 (Multi-Server + Voice)", inline=True)
    embed.add_field(name="Серверов", value=len(bot.guilds), inline=True)
    embed.add_field(name="Пользователей", value=len(bot.users), inline=True)
    
    channel_id = config.get_log_channel_id(ctx.guild.id)
    channel_info = f"<#{channel_id}>" if channel_id else "Не установлен"
    embed.add_field(name="Канал логов", value=channel_info, inline=False)
    
    # Информация о голосовом подключении
    if ctx.guild.voice_client:
        voice_channel = ctx.guild.voice_client.channel
        voice_info = f"🔊 {voice_channel.mention}"
    else:
        voice_info = "❌ Не подключен"
    
    embed.add_field(name="Голосовое подключение", value=voice_info, inline=False)
    
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
        print("Установите переменную окружения DISCORD_BOT_TOKEN или отредактируйте multi_server_config.json")
        exit(1)
    
    try:
        bot.start_time = datetime.utcnow()
        bot.run(config.token)
    except discord.LoginFailure:
        print("❌ Ошибка: Неверный токен бота!")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
