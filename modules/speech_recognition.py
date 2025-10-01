"""
Модуль для распознавания речи
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple
import speech_recognition as sr
import pydub
from pydub import AudioSegment
import aiofiles

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self, config):
        self.config = config
        self.recognizer = sr.Recognizer()
        
        # Настройка распознавателя речи
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
        # Создаем папки для логов речи
        self.ensure_voice_logs_dirs()
    
    def ensure_voice_logs_dirs(self):
        """Создает папки для логов речи каждого сервера"""
        # Эта функция будет вызвана после инициализации бота
        pass
    
    def create_voice_logs_dir(self, guild_id: int):
        """Создает папку для логов речи конкретного сервера"""
        voice_logs_dir = f"voice_logs_{guild_id}"
        if not os.path.exists(voice_logs_dir):
            os.makedirs(voice_logs_dir)
            logger.info(f"Создана папка для логов речи: {voice_logs_dir}")
    
    async def test_recognition(self, audio_file_path: str) -> Optional[str]:
        """Тестирует распознавание речи на файле"""
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"Файл не найден: {audio_file_path}")
                return None
            
            # Загружаем аудио файл
            audio = AudioSegment.from_file(audio_file_path)
            
            # Проверяем длительность
            duration = len(audio) / 1000.0
            if duration < self.config.min_audio_duration or duration > self.config.max_audio_duration:
                logger.warning(f"Длительность аудио {duration}с не подходит (мин: {self.config.min_audio_duration}с, макс: {self.config.max_audio_duration}с)")
                return None
            
            # Конвертируем в формат для распознавания
            wav_data = audio.export(format="wav")
            wav_data.seek(0)
            
            # Распознаем речь
            with sr.AudioFile(wav_data) as source:
                audio_data = self.recognizer.record(source)
            
            try:
                text = self.recognizer.recognize_google(audio_data, language=self.config.speech_language)
                logger.info(f"Распознанный текст: {text}")
                return text
            except sr.UnknownValueError:
                logger.warning("Речь не распознана")
                return None
            except sr.RequestError as e:
                logger.error(f"Ошибка сервиса распознавания речи: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка тестирования распознавания речи: {e}")
            return None
    
    async def log_speech(self, guild_id: int, user_id: int, text: str, timestamp: datetime):
        """Логирует распознанную речь в файл"""
        try:
            self.create_voice_logs_dir(guild_id)
            voice_logs_dir = f"voice_logs_{guild_id}"
            voice_file = os.path.join(voice_logs_dir, "voice.txt")
            
            # Форматируем запись
            log_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] User {user_id}: {text}\n"
            
            # Записываем в файл асинхронно
            async with aiofiles.open(voice_file, 'a', encoding='utf-8') as f:
                await f.write(log_entry)
            
            logger.info(f"Распознана речь на сервере {guild_id}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Ошибка записи речи в файл: {e}")
    
    async def get_voice_logs_stats(self, guild_id: int) -> dict:
        """Получает статистику файлов с распознанной речью"""
        voice_logs_dir = f"voice_logs_{guild_id}"
        voice_file = os.path.join(voice_logs_dir, "voice.txt")
        
        stats = {
            'exists': False,
            'size': 0,
            'lines': 0,
            'recent_lines': []
        }
        
        if os.path.exists(voice_file):
            stats['exists'] = True
            stats['size'] = os.path.getsize(voice_file)
            
            try:
                async with aiofiles.open(voice_file, 'r', encoding='utf-8') as f:
                    lines = await f.readlines()
                    stats['lines'] = len(lines)
                    stats['recent_lines'] = lines[-5:] if lines else []
            except Exception as e:
                logger.error(f"Ошибка чтения файла логов: {e}")
        
        return stats
    
    def clear_voice_logs(self, guild_id: int) -> bool:
        """Очищает файл с распознанной речью"""
        try:
            voice_logs_dir = f"voice_logs_{guild_id}"
            voice_file = os.path.join(voice_logs_dir, "voice.txt")
            
            if os.path.exists(voice_file):
                os.remove(voice_file)
                logger.info(f"Файл логов очищен для сервера {guild_id}")
                return True
            else:
                logger.warning(f"Файл логов не найден для сервера {guild_id}")
                return False
        except Exception as e:
            logger.error(f"Ошибка очистки файла логов: {e}")
            return False
