"""
Модуль для логирования событий Discord
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
import discord

logger = logging.getLogger(__name__)

class DiscordLogger:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.rate_limits = {}
    
    async def get_log_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Получает канал для логов конкретного сервера"""
        channel_id = self.config.get_log_channel_id(guild_id)
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
    
    async def log_voice_state_update(self, member, before, after):
        """Логирует изменения голосового состояния"""
        if not self.config.log_voice or before.channel == after.channel or not member.guild:
            return
        
        if before.channel is None:
            # Подключился к голосовому каналу
            await self.send_log(
                guild_id=member.guild.id,
                title="🎤 Подключился к голосовому каналу",
                description=f"**Пользователь:** {self.format_user_info(member)}\n**Канал:** {after.channel.mention}",
                color=discord.Color.green(),
                fields=[
                    ("Участников в канале", str(len(after.channel.members)), True),
                    ("Распознавание речи", "✅ Включено" if self.config.speech_recognition else "❌ Выключено", True)
                ],
                thumbnail=member.display_avatar.url
            )
        elif after.channel is None:
            # Отключился от голосового канала
            await self.send_log(
                guild_id=member.guild.id,
                title="🎤 Отключился от голосового канала",
                description=f"**Пользователь:** {self.format_user_info(member)}\n**Канал:** {before.channel.mention}",
                color=discord.Color.red(),
                fields=[
                    ("Участников в канале", str(len(before.channel.members)), True)
                ],
                thumbnail=member.display_avatar.url
            )
        else:
            # Перешел в другой голосовой канал
            await self.send_log(
                guild_id=member.guild.id,
                title="🎤 Перешел в другой голосовой канал",
                description=f"**Пользователь:** {self.format_user_info(member)}",
                color=discord.Color.blue(),
                fields=[
                    ("Из", before.channel.mention, True),
                    ("В", after.channel.mention, True),
                    ("Участников в новом канале", str(len(after.channel.members)), True)
                ],
                thumbnail=member.display_avatar.url
            )
