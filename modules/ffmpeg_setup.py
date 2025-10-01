"""
Модуль для автоматической установки FFmpeg
"""
import os
import subprocess
import platform
import urllib.request
import zipfile
import shutil
import logging

logger = logging.getLogger(__name__)

def setup_ffmpeg():
    """Устанавливает FFmpeg если его нет"""
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg")
    
    if not os.path.exists(ffmpeg_path):
        logger.info("FFmpeg не найден, начинаем установку...")
        
        try:
            system = platform.system().lower()
            
            if system == "windows":
                install_ffmpeg_windows()
            elif system == "linux":
                install_ffmpeg_linux()
            elif system == "darwin":  # macOS
                install_ffmpeg_macos()
            else:
                logger.warning(f"Неподдерживаемая операционная система: {system}")
                logger.info("Пожалуйста, установите FFmpeg вручную:")
                logger.info("https://ffmpeg.org/download.html")
                
        except Exception as e:
            logger.error(f"Ошибка установки FFmpeg: {e}")
            logger.info("Пожалуйста, установите FFmpeg вручную:")
            logger.info("Windows: https://ffmpeg.org/download.html")
            logger.info("Linux: sudo apt install ffmpeg")
            logger.info("macOS: brew install ffmpeg")
    else:
        logger.info("FFmpeg уже установлен")

def install_ffmpeg_windows():
    """Устанавливает FFmpeg для Windows"""
    try:
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        ffmpeg_zip = "ffmpeg.zip"
        
        logger.info("Скачиваем FFmpeg для Windows...")
        urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
        
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        # Находим папку с FFmpeg
        for item in os.listdir("."):
            if item.startswith("ffmpeg-master") and os.path.isdir(item):
                shutil.move(item, "ffmpeg")
                break
        
        os.remove(ffmpeg_zip)
        logger.info("FFmpeg установлен успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка установки FFmpeg для Windows: {e}")
        raise

def install_ffmpeg_linux():
    """Устанавливает FFmpeg для Linux"""
    try:
        logger.info("Пытаемся установить FFmpeg через apt...")
        subprocess.run(["sudo", "apt", "update"], check=False)
        subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=False)
        logger.info("FFmpeg установлен через apt!")
        
    except Exception as e:
        logger.error(f"Ошибка установки FFmpeg для Linux: {e}")
        raise

def install_ffmpeg_macos():
    """Устанавливает FFmpeg для macOS"""
    try:
        logger.info("Пытаемся установить FFmpeg через Homebrew...")
        subprocess.run(["brew", "install", "ffmpeg"], check=False)
        logger.info("FFmpeg установлен через Homebrew!")
        
    except Exception as e:
        logger.error(f"Ошибка установки FFmpeg для macOS: {e}")
        raise

def check_ffmpeg():
    """Проверяет, установлен ли FFmpeg"""
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg")
    return os.path.exists(ffmpeg_path)

def get_ffmpeg_path():
    """Возвращает путь к FFmpeg"""
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg")
    if os.path.exists(ffmpeg_path):
        # Ищем исполняемый файл
        for root, dirs, files in os.walk(ffmpeg_path):
            for file in files:
                if file == "ffmpeg.exe" or file == "ffmpeg":
                    return os.path.join(root, file)
    return "ffmpeg"  # Fallback к системному FFmpeg
