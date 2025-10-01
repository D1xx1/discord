"""
Модуль команд бота
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class BotCommands:
    def __init__(self, bot, config, discord_logger):
        self.bot = bot
        self.config = config
        self.discord_logger = discord_logger
    
    def setup_commands(self):
        """Настраивает команды бота"""
        
        @self.bot.command(name='setlogchannel')
        @commands.has_permissions(administrator=True)
        async def set_log_channel(ctx, channel: discord.TextChannel):
            """Устанавливает канал для логов на текущем сервере"""
            self.config.set_log_channel_id(ctx.guild.id, channel.id)
            
            await ctx.send(f"✅ Канал для логов установлен: {channel.mention}\n"
                          f"Теперь все логи сервера **{ctx.guild.name}** будут отправляться в этот канал!")
        
        
        @self.bot.command(name='logstatus')
        @commands.has_permissions(administrator=True)
        async def log_status(ctx):
            """Показывает статус логирования для сервера"""
            embed = discord.Embed(
                title="📊 Статус логирования",
                color=discord.Color.blue()
            )
            
            # Статус канала логов
            channel_id = self.config.get_log_channel_id(ctx.guild.id)
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                channel_info = f"✅ {channel.mention}" if channel else f"❌ Канал не найден (ID: {channel_id})"
            else:
                channel_info = "❌ Не установлен"
            
            embed.add_field(name="Канал логов", value=channel_info, inline=False)
            
            # Статус типов логов
            embed.add_field(name="📝 Сообщения", value="✅ Включено" if self.config.log_messages else "❌ Выключено", inline=True)
            embed.add_field(name="👥 Участники", value="✅ Включено" if self.config.log_members else "❌ Выключено", inline=True)
            embed.add_field(name="📁 Каналы", value="✅ Включено" if self.config.log_channels else "❌ Выключено", inline=True)
            embed.add_field(name="🎭 Роли", value="✅ Включено" if self.config.log_roles else "❌ Выключено", inline=True)
            embed.add_field(name="🎤 Голос", value="✅ Включено" if self.config.log_voice else "❌ Выключено", inline=True)
            
            # Статистика сервера
            embed.add_field(name="Участников", value=str(ctx.guild.member_count), inline=True)
            embed.add_field(name="Каналов", value=str(len(ctx.guild.channels)), inline=True)
            embed.add_field(name="Ролей", value=str(len(ctx.guild.roles)), inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='togglelogs')
        @commands.has_permissions(administrator=True)
        async def toggle_logs(ctx, log_type: str = None):
            """Включает/выключает определенный тип логов"""
            if not log_type:
                await ctx.send("❌ Укажите тип логов!\n"
                              "Доступные типы: `messages`, `members`, `channels`, `roles`, `voice`")
                return
            
            log_type = log_type.lower()
            log_map = {
                'messages': 'log_messages',
                'members': 'log_members', 
                'channels': 'log_channels',
                'roles': 'log_roles',
                'voice': 'log_voice'
            }
            
            if log_type not in log_map:
                await ctx.send("❌ Неверный тип логов!\n"
                              "Доступные типы: `messages`, `members`, `channels`, `roles`, `voice`")
                return
            
            # Переключаем настройку
            current_value = getattr(self.config, log_map[log_type])
            setattr(self.config, log_map[log_type], not current_value)
            self.config.save_config()
            
            new_value = getattr(self.config, log_map[log_type])
            status = "включено" if new_value else "выключено"
            emoji = "✅" if new_value else "❌"
            
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title=f"{emoji} Логирование {log_type} изменено",
                description=f"**Статус:** {status.title()}\n**Изменил:** {ctx.author.mention}",
                color=discord.Color.green() if new_value else discord.Color.red(),
                fields=[
                    ("Время изменения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S UTC'), True)
                ]
            )
            
            await ctx.send(f"✅ Логирование **{log_type}** {status}!")
        
        @self.bot.command(name='serverlist')
        @commands.has_permissions(administrator=True)
        async def server_list(ctx):
            """Показывает список всех серверов и их каналов логов"""
            embed = discord.Embed(
                title="🌐 Список серверов",
                description=f"Бот подключен к **{len(self.bot.guilds)}** серверам",
                color=discord.Color.blue()
            )
            
            for guild in self.bot.guilds:
                channel_id = self.config.get_log_channel_id(guild.id)
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    channel_info = f"✅ #{channel.name}" if channel else f"❌ Канал не найден"
                else:
                    channel_info = "❌ Не настроен"
                
                embed.add_field(
                    name=guild.name,
                    value=f"**Канал логов:** {channel_info}\n**Участников:** {guild.member_count}",
                    inline=True
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='testlog')
        @commands.has_permissions(administrator=True)
        async def test_log(ctx):
            """Отправляет тестовый лог"""
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title="🧪 Тестовый лог",
                description=f"**Тест выполнил:** {ctx.author.mention}\n**Время:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S UTC')}",
                color=discord.Color.green(),
                fields=[
                    ("Сервер", ctx.guild.name, True),
                    ("Канал", ctx.channel.mention, True),
                    ("Статус", "✅ Логирование работает", True)
                ],
                thumbnail=ctx.author.display_avatar.url
            )
            
            await ctx.send("✅ Тестовый лог отправлен!")
        
        @self.bot.command(name='botinfo')
        async def bot_info(ctx):
            """Информация о боте"""
            embed = discord.Embed(
                title="🤖 Информация о боте",
                color=discord.Color.blue()
            )
            embed.add_field(name="Версия", value="1.0.0", inline=True)
            embed.add_field(name="Фреймворк", value="Discord.py", inline=True)
            embed.add_field(name="Серверов", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="Пользователей", value=len(self.bot.users), inline=True)
            
            channel_id = self.config.get_log_channel_id(ctx.guild.id)
            channel_info = f"<#{channel_id}>" if channel_id else "Не установлен"
            embed.add_field(name="Канал логов", value=channel_info, inline=False)
            
            embed.add_field(name="Префикс", value=self.config.prefix, inline=True)
            embed.add_field(name="Задержка", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
            
            await ctx.send(embed=embed)
