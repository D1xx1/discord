"""
Discord бот
"""
import asyncio
import logging
from datetime import datetime
import discord
from discord.ext import commands

# Импортируем модули
from modules.config import BotConfig
from modules.logger import DiscordLogger
from modules.commands import BotCommands

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


# Загружаем конфигурацию
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
intents.presences = True  # Для отслеживания статуса пользователей

# Создаем бота
bot = commands.Bot(command_prefix=config.prefix, intents=intents)

# Инициализируем модули
discord_logger = DiscordLogger(bot, config)
bot_commands = BotCommands(bot, config, discord_logger)

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
            name=f"за всеми"
        )
    )

# === СОБЫТИЯ СООБЩЕНИЙ ===
@bot.event
async def on_message(message):
    """Обработка новых сообщений"""
    if not message.author.bot and not message.guild is None:
        await discord_logger.log_message_create(message)
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    """Логирование редактирования сообщений"""
    if not after.author.bot and not after.guild is None:
        await discord_logger.log_message_edit(before, after)

@bot.event
async def on_message_delete(message):
    """Логирование удаления сообщений"""
    if not message.author.bot and not message.guild is None:
        await discord_logger.log_message_delete(message)

@bot.event
async def on_bulk_message_delete(messages):
    """Логирование массового удаления сообщений"""
    if messages and not messages[0].author.bot and not messages[0].guild is None:
        await discord_logger.log_bulk_message_delete(messages)

# === СОБЫТИЯ УЧАСТНИКОВ ===
@bot.event
async def on_member_join(member):
    """Логирование присоединения участника"""
    await discord_logger.log_member_join(member)

@bot.event
async def on_member_remove(member):
    """Логирование выхода участника"""
    await discord_logger.log_member_remove(member)

@bot.event
async def on_member_update(before, after):
    """Логирование обновления участника"""
    await discord_logger.log_member_update(before, after)

@bot.event
async def on_user_update(before, after):
    """Логирование обновления пользователя"""
    await discord_logger.log_user_update(before, after)

# === СОБЫТИЯ СТАТУСА ПОЛЬЗОВАТЕЛЕЙ ===
@bot.event
async def on_presence_update(before, after):
    """Логирование изменений статуса пользователя (онлайн/офлайн)"""
    await discord_logger.log_presence_update(before, after)

@bot.event
async def on_user_activity_update(before, after):
    """Логирование изменений активности пользователя (игра, стрим и т.д.)"""
    await discord_logger.log_user_activity_update(before, after)

# === СОБЫТИЯ КАНАЛОВ ===
@bot.event
async def on_guild_channel_create(channel):
    """Логирование создания канала"""
    await discord_logger.log_channel_create(channel)

@bot.event
async def on_guild_channel_delete(channel):
    """Логирование удаления канала"""
    await discord_logger.log_channel_delete(channel)

@bot.event
async def on_guild_channel_update(before, after):
    """Логирование обновления канала"""
    await discord_logger.log_channel_update(before, after)

# === СОБЫТИЯ РОЛЕЙ ===
@bot.event
async def on_guild_role_create(role):
    """Логирование создания роли"""
    await discord_logger.log_role_create(role)

@bot.event
async def on_guild_role_delete(role):
    """Логирование удаления роли"""
    await discord_logger.log_role_delete(role)

@bot.event
async def on_guild_role_update(before, after):
    """Логирование обновления роли"""
    await discord_logger.log_role_update(before, after)

# === СОБЫТИЯ РЕАКЦИЙ ===
@bot.event
async def on_reaction_add(reaction, user):
    """Логирование добавления реакции"""
    if not user.bot and not reaction.message.guild is None:
        await discord_logger.log_reaction_add(reaction, user)

@bot.event
async def on_reaction_remove(reaction, user):
    """Логирование удаления реакции"""
    if not user.bot and not reaction.message.guild is None:
        await discord_logger.log_reaction_remove(reaction, user)

@bot.event
async def on_reaction_clear(message, reactions):
    """Логирование очистки всех реакций"""
    if not message.guild is None:
        await discord_logger.log_reaction_clear(message, reactions)

# === СОБЫТИЯ ГОЛОСОВЫХ КАНАЛОВ ===
@bot.event
async def on_voice_state_update(member, before, after):
    """Логирование изменений голосового состояния"""
    await discord_logger.log_voice_state_update(member, before, after)

# === СОБЫТИЯ СЕРВЕРА ===
@bot.event
async def on_guild_update(before, after):
    """Логирование обновления сервера"""
    await discord_logger.log_guild_update(before, after)

# События эмодзи и стикеров (опциональные, требуют специальных интентов)
# @bot.event
# async def on_guild_emojis_update(guild, before, after):
#     """Логирование обновления эмодзи сервера"""
#     await discord_logger.log_guild_emojis_update(guild, before, after)

# @bot.event
# async def on_guild_stickers_update(guild, before, after):
#     """Логирование обновления стикеров сервера"""
#     await discord_logger.log_guild_stickers_update(guild, before, after)


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

def main():
    """Основная функция запуска бота"""
    if config.token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Не установлен токен бота!")
        print("Установите переменную окружения DISCORD_BOT_TOKEN или отредактируйте config.json")
        return
    
    try:
        # Настраиваем команды
        bot_commands.setup_commands()
        
        # Запускаем бота
        bot.start_time = datetime.utcnow()
        bot.run(config.token)
    except discord.LoginFailure:
        print("❌ Ошибка: Неверный токен бота!")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
