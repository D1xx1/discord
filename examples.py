"""
Примеры использования Discord Logger Bot
"""

import discord
from discord.ext import commands
import asyncio

# Пример кастомного логгера для специфических событий
class CustomLogger:
    def __init__(self, bot, log_channel_id):
        self.bot = bot
        self.log_channel_id = log_channel_id
    
    async def log_custom_event(self, title, description, **kwargs):
        """Пример кастомного логгера"""
        channel = self.bot.get_channel(self.log_channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=kwargs.get('color', discord.Color.blue()),
            timestamp=discord.utils.utcnow()
        )
        
        if 'fields' in kwargs:
            for field in kwargs['fields']:
                embed.add_field(**field)
        
        await channel.send(embed=embed)

# Пример расширения бота с дополнительными функциями
class ExtendedLoggerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_logger = None
    
    async def on_ready(self):
        print(f'{self.user} готов к работе!')
        self.custom_logger = CustomLogger(self, YOUR_LOG_CHANNEL_ID)
    
    async def on_member_ban(self, guild, user):
        """Логирование банов"""
        if self.custom_logger:
            await self.custom_logger.log_custom_event(
                title="🔨 Пользователь забанен",
                description=f"**Пользователь:** {user.mention} (`{user.id}`)",
                color=discord.Color.red(),
                fields=[
                    {"name": "Сервер", "value": guild.name, "inline": True},
                    {"name": "Время", "value": discord.utils.utcnow().strftime('%d.%m.%Y %H:%M:%S'), "inline": True}
                ]
            )
    
    async def on_member_unban(self, guild, user):
        """Логирование разбанов"""
        if self.custom_logger:
            await self.custom_logger.log_custom_event(
                title="🔓 Пользователь разбанен",
                description=f"**Пользователь:** {user.mention} (`{user.id}`)",
                color=discord.Color.green(),
                fields=[
                    {"name": "Сервер", "value": guild.name, "inline": True},
                    {"name": "Время", "value": discord.utils.utcnow().strftime('%d.%m.%Y %H:%M:%S'), "inline": True}
                ]
            )

# Пример команды для отправки кастомного лога
@commands.command(name='customlog')
@commands.has_permissions(administrator=True)
async def custom_log(ctx, *, message):
    """Отправляет кастомный лог"""
    # Получаем канал логов из конфигурации
    log_channel_id = 1234567890123456789  # Замените на ваш ID канала
    
    custom_logger = CustomLogger(ctx.bot, log_channel_id)
    await custom_logger.log_custom_event(
        title="📝 Кастомный лог",
        description=message,
        color=discord.Color.purple(),
        fields=[
            {"name": "Автор команды", "value": ctx.author.mention, "inline": True},
            {"name": "Сервер", "value": ctx.guild.name, "inline": True}
        ]
    )
    
    await ctx.send("✅ Кастомный лог отправлен!")

# Пример фильтрации сообщений
def should_log_message(message):
    """Определяет, нужно ли логировать сообщение"""
    # Не логируем сообщения ботов
    if message.author.bot:
        return False
    
    # Не логируем сообщения в определенных каналах
    no_log_channels = ['general', 'off-topic']
    if message.channel.name in no_log_channels:
        return False
    
    # Логируем только сообщения длиннее 10 символов
    if len(message.content) < 10:
        return False
    
    # Логируем сообщения с упоминаниями
    if message.mentions:
        return True
    
    # Логируем сообщения с вложениями
    if message.attachments:
        return True
    
    return True

# Пример системы уведомлений
class NotificationSystem:
    def __init__(self, bot, log_channel_id):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.notification_rules = {}
    
    def add_rule(self, event_type, condition, notification_text):
        """Добавляет правило уведомления"""
        if event_type not in self.notification_rules:
            self.notification_rules[event_type] = []
        
        self.notification_rules[event_type].append({
            'condition': condition,
            'text': notification_text
        })
    
    async def check_rules(self, event_type, data):
        """Проверяет правила для события"""
        if event_type not in self.notification_rules:
            return
        
        channel = self.bot.get_channel(self.log_channel_id)
        if not channel:
            return
        
        for rule in self.notification_rules[event_type]:
            if rule['condition'](data):
                embed = discord.Embed(
                    title="🚨 Уведомление",
                    description=rule['text'],
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)

# Пример использования системы уведомлений
def setup_notifications(bot, log_channel_id):
    """Настраивает систему уведомлений"""
    notification_system = NotificationSystem(bot, log_channel_id)
    
    # Уведомление о новых аккаунтах
    notification_system.add_rule(
        'member_join',
        lambda member: (discord.utils.utcnow() - member.created_at).days < 1,
        f"⚠️ Новый аккаунт присоединился к серверу!"
    )
    
    # Уведомление о массовых удалениях сообщений
    notification_system.add_rule(
        'message_delete',
        lambda message: len(message.content) > 100,
        f"⚠️ Удалено длинное сообщение!"
    )
    
    return notification_system

if __name__ == "__main__":
    print("Это файл с примерами использования Discord Logger Bot")
    print("Импортируйте нужные функции в ваш основной файл бота")
