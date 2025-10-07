"""
Модуль конфигурации бота
"""
import os
import json
from typing import Optional, Dict

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
        self.log_presence = os.getenv('LOG_PRESENCE', 'true').lower() == 'true'
        # Словарь для хранения каналов логов для каждого сервера
        self.server_log_channels: Dict[str, int] = {}
        
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
                    self.log_presence = config.get('log_presence', self.log_presence)
                    self.server_log_channels = config.get('server_log_channels', {})
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
    
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
            'log_presence': self.log_presence,
            'server_log_channels': self.server_log_channels
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
