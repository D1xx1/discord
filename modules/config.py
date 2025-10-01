"""
Модуль конфигурации бота
"""
import os
import json
from typing import Optional, Dict, Set

class BotConfig:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.token = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        self.prefix = os.getenv('BOT_PREFIX', '!')
        self.log_messages = os.getenv('LOG_MESSAGES', 'true').lower() == 'true'
        self.log_voice = os.getenv('LOG_VOICE', 'true').lower() == 'true'
        self.log_members = os.getenv('LOG_MEMBERS', 'true').lower() == 'true'
        self.log_channels = os.getenv('LOG_CHANNELS', 'true').lower() == 'true'
        self.log_roles = os.getenv('LOG_ROLES', 'true').lower() == 'true'
        self.speech_recognition = os.getenv('SPEECH_RECOGNITION', 'true').lower() == 'true'
        
        # Словарь для хранения каналов логов для каждого сервера
        self.server_log_channels: Dict[str, int] = {}
        
        # Словарь для исключенных пользователей (по серверам)
        self.excluded_users: Dict[int, Set[int]] = {}
        
        # Настройки распознавания речи
        self.speech_language = 'ru-RU'
        self.min_audio_duration = 0.5
        self.max_audio_duration = 30
        
        # Загружаем конфигурацию из файла
        self.load_config()
    
    def load_config(self):
        """Загружает конфигурацию из файла"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.token = config.get('token', self.token)
                    self.prefix = config.get('prefix', self.prefix)
                    self.log_messages = config.get('log_messages', self.log_messages)
                    self.log_voice = config.get('log_voice', self.log_voice)
                    self.log_members = config.get('log_members', self.log_members)
                    self.log_channels = config.get('log_channels', self.log_channels)
                    self.log_roles = config.get('log_roles', self.log_roles)
                    self.speech_recognition = config.get('speech_recognition', self.speech_recognition)
                    self.server_log_channels = config.get('server_log_channels', {})
                    self.excluded_users = {int(k): set(v) for k, v in config.get('excluded_users', {}).items()}
                    self.speech_language = config.get('speech_language', self.speech_language)
                    self.min_audio_duration = config.get('min_audio_duration', self.min_audio_duration)
                    self.max_audio_duration = config.get('max_audio_duration', self.max_audio_duration)
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
    
    def get_log_channel_id(self, guild_id: int) -> Optional[int]:
        """Получает ID канала логов для конкретного сервера"""
        return self.server_log_channels.get(str(guild_id))
    
    def set_log_channel_id(self, guild_id: int, channel_id: int):
        """Устанавливает ID канала логов для конкретного сервера"""
        self.server_log_channels[str(guild_id)] = channel_id
        self.save_config()
    
    def add_excluded_user(self, guild_id: int, user_id: int):
        """Добавляет пользователя в список исключенных для сервера"""
        if guild_id not in self.excluded_users:
            self.excluded_users[guild_id] = set()
        self.excluded_users[guild_id].add(user_id)
        self.save_config()
    
    def remove_excluded_user(self, guild_id: int, user_id: int):
        """Удаляет пользователя из списка исключенных для сервера"""
        if guild_id in self.excluded_users:
            self.excluded_users[guild_id].discard(user_id)
            if not self.excluded_users[guild_id]:
                del self.excluded_users[guild_id]
        self.save_config()
    
    def is_user_excluded(self, guild_id: int, user_id: int) -> bool:
        """Проверяет, исключен ли пользователь для сервера"""
        return user_id in self.excluded_users.get(guild_id, set())
    
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
            'speech_recognition': self.speech_recognition,
            'server_log_channels': self.server_log_channels,
            'excluded_users': {str(k): list(v) for k, v in self.excluded_users.items()},
            'speech_language': self.speech_language,
            'min_audio_duration': self.min_audio_duration,
            'max_audio_duration': self.max_audio_duration
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
