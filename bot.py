"""
Discord бот с полноценным распознаванием речи в голосовых каналах
"""
import asyncio
import logging
from datetime import datetime
import discord
from discord.ext import commands

# Импортируем модули
from modules.config import BotConfig
from modules.ffmpeg_setup import setup_ffmpeg, check_ffmpeg
from modules.speech_recognition import SpeechRecognizer
from modules.logger import DiscordLogger
from modules.commands import BotCommands
from modules.simple_voice_recorder import SimpleVoiceRecorder

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

# Устанавливаем FFmpeg при запуске
logger.info("Проверяем и устанавливаем FFmpeg...")
setup_ffmpeg()

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

# Создаем бота
bot = commands.Bot(command_prefix=config.prefix, intents=intents)

# Инициализируем модули
speech_recognizer = SpeechRecognizer(config)
discord_logger = DiscordLogger(bot, config)
voice_recorder = SimpleVoiceRecorder(config, speech_recognizer)
bot_commands = BotCommands(bot, config, discord_logger, speech_recognizer, voice_recorder)

@bot.event
async def on_ready():
    """Событие запуска бота"""
    logger.info(f'{bot.user} успешно запущен!')
    logger.info(f'Бот подключен к {len(bot.guilds)} серверам')
    
    # Создаем папки для логов речи
    for guild in bot.guilds:
        speech_recognizer.create_voice_logs_dir(guild.id)
    
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
    ffmpeg_status = "✅ FFmpeg" if check_ffmpeg() else "❌ No FFmpeg"
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"за всеми"
        )
    )

@bot.event
async def on_voice_state_update(member, before, after):
    """Логирование изменений голосового состояния"""
    await discord_logger.log_voice_state_update(member, before, after)

@bot.event
async def on_voice_client_disconnect(voice_client):
    """Обработка отключения от голосового канала"""
    try:
        guild_id = voice_client.guild.id
        if voice_recorder.is_recording(guild_id):
            await voice_recorder.stop_recording(guild_id)
            logger.info(f"Остановлена запись голоса на сервере {guild_id} из-за отключения")
    except Exception as e:
        logger.error(f"Ошибка при отключении от голосового канала: {e}")

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
        print("Установите переменную окружения DISCORD_BOT_TOKEN или отредактируйте working_speech_config.json")
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
