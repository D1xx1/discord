"""
Модуль команд бота
"""
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class BotCommands:
    def __init__(self, bot, config, discord_logger):
        self.bot = bot
        self.config = config
        self.discord_logger = discord_logger
    
    def format_time(self):
        """Форматирует время для отображения в UTC+7 (Новосибирское)"""
        dt = datetime.utcnow()
        novosibirsk_tz = timezone(timedelta(hours=7))
        dt = dt.replace(tzinfo=timezone.utc)
        local_time = dt.astimezone(novosibirsk_tz)
        return local_time.strftime('%d.%m.%Y %H:%M:%S MSK+4')
    
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
            embed.add_field(name="📱 Статус", value="✅ Включено" if self.config.log_presence else "❌ Выключено", inline=True)
            
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
                              "Доступные типы: `messages`, `members`, `channels`, `roles`, `voice`, `presence`")
                return
            
            log_type = log_type.lower()
            log_map = {
                'messages': 'log_messages',
                'members': 'log_members', 
                'channels': 'log_channels',
                'roles': 'log_roles',
                'voice': 'log_voice',
                'presence': 'log_presence'
            }
            
            if log_type not in log_map:
                await ctx.send("❌ Неверный тип логов!\n"
                              "Доступные типы: `messages`, `members`, `channels`, `roles`, `voice`, `presence`")
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
                    ("Время изменения", self.format_time(), True)
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
                description=f"**Тест выполнил:** {ctx.author.mention}\n**Время:** {self.format_time()}",
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
        
        # === ГОЛОСОВЫЕ КОМАНДЫ ===
        
        @self.bot.command(name='join', aliases=['j'])
        async def join_voice(ctx):
            """Подключается к голосовому каналу пользователя"""
            if not ctx.author.voice:
                await ctx.send("❌ Вы должны находиться в голосовом канале!")
                return
            
            channel = ctx.author.voice.channel
            
            # Если бот уже подключен к голосовому каналу
            if ctx.voice_client:
                if ctx.voice_client.channel == channel:
                    await ctx.send(f"✅ Я уже подключен к каналу **{channel.name}**!")
                    return
                else:
                    await ctx.voice_client.move_to(channel)
                    await ctx.send(f"🔄 Перемещен в канал **{channel.name}**!")
                    
                    # Логируем перемещение
                    await self.discord_logger.send_log(
                        guild_id=ctx.guild.id,
                        title="🎤 Бот перемещен в голосовой канал",
                        description=f"**Канал:** {channel.mention}\n**Команду выполнил:** {ctx.author.mention}",
                        color=discord.Color.blue(),
                        fields=[
                            ("Участников в канале", str(len(channel.members)), True),
                            ("Время", self.format_time(), True)
                        ],
                        thumbnail=ctx.author.display_avatar.url
                    )
                    return
            
            try:
                await channel.connect()
                await ctx.send(f"✅ Подключен к каналу **{channel.name}**!")
                
                # Логируем подключение
                await self.discord_logger.send_log(
                    guild_id=ctx.guild.id,
                    title="🎤 Бот подключился к голосовому каналу",
                    description=f"**Канал:** {channel.mention}\n**Команду выполнил:** {ctx.author.mention}",
                    color=discord.Color.green(),
                    fields=[
                        ("Участников в канале", str(len(channel.members)), True),
                        ("Время подключения", self.format_time(), True)
                    ],
                    thumbnail=ctx.author.display_avatar.url
                )
            except discord.ClientException:
                await ctx.send("❌ Бот уже подключен к голосовому каналу!")
            except discord.opus.OpusNotLoaded:
                await ctx.send("❌ Ошибка: Opus не загружен!")
            except Exception as e:
                logger.error(f"Ошибка подключения к голосовому каналу: {e}")
                await ctx.send(f"❌ Ошибка при подключении: {e}")
        
        @self.bot.command(name='leave', aliases=['disconnect', 'dc'])
        async def leave_voice(ctx):
            """Отключается от голосового канала"""
            if not ctx.voice_client:
                await ctx.send("❌ Бот не подключен к голосовому каналу!")
                return
            
            channel = ctx.voice_client.channel
            await ctx.voice_client.disconnect()
            await ctx.send(f"👋 Отключен от канала **{channel.name}**!")
            
            # Логируем отключение
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title="🎤 Бот отключился от голосового канала",
                description=f"**Канал:** {channel.mention}\n**Команду выполнил:** {ctx.author.mention}",
                color=discord.Color.red(),
                fields=[
                    ("Время отключения", self.format_time(), True)
                ],
                thumbnail=ctx.author.display_avatar.url
            )
        
        @self.bot.command(name='move', aliases=['mv'])
        async def move_voice(ctx, *, channel_name: str = None):
            """Перемещает бота в другой голосовой канал"""
            if not ctx.voice_client:
                await ctx.send("❌ Бот не подключен к голосовому каналу!")
                return
            
            if channel_name:
                # Ищем канал по имени
                channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
                if not channel:
                    await ctx.send(f"❌ Голосовой канал **{channel_name}** не найден!")
                    return
            else:
                # Перемещаемся к пользователю
                if not ctx.author.voice:
                    await ctx.send("❌ Укажите название канала или зайдите в голосовой канал!")
                    return
                channel = ctx.author.voice.channel
            
            old_channel = ctx.voice_client.channel
            
            try:
                await ctx.voice_client.move_to(channel)
                await ctx.send(f"🔄 Перемещен из **{old_channel.name}** в **{channel.name}**!")
                
                # Логируем перемещение
                await self.discord_logger.send_log(
                    guild_id=ctx.guild.id,
                    title="🎤 Бот перемещен в другой голосовой канал",
                    description=f"**Команду выполнил:** {ctx.author.mention}",
                    color=discord.Color.blue(),
                    fields=[
                        ("Из канала", old_channel.mention, True),
                        ("В канал", channel.mention, True),
                        ("Участников в новом канале", str(len(channel.members)), True),
                        ("Время", self.format_time(), True)
                    ],
                    thumbnail=ctx.author.display_avatar.url
                )
            except Exception as e:
                logger.error(f"Ошибка перемещения: {e}")
                await ctx.send(f"❌ Ошибка при перемещении: {e}")
        
        @self.bot.command(name='voiceinfo', aliases=['vi'])
        async def voice_info(ctx):
            """Показывает информацию о текущем голосовом подключении"""
            if not ctx.voice_client:
                await ctx.send("❌ Бот не подключен к голосовому каналу!")
                return
            
            channel = ctx.voice_client.channel
            
            # Получаем список участников канала
            members_list = [member.mention for member in channel.members if not member.bot]
            members_text = ", ".join(members_list) if members_list else "Только боты"
            
            embed = discord.Embed(
                title=f"🎤 Голосовой канал: {channel.name}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Всего участников", value=str(len(channel.members)), inline=True)
            embed.add_field(name="Битрейт", value=f"{channel.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="Лимит пользователей", value=str(channel.user_limit) if channel.user_limit > 0 else "Без лимита", inline=True)
            embed.add_field(name="Категория", value=channel.category.name if channel.category else "Без категории", inline=True)
            embed.add_field(name="ID канала", value=str(channel.id), inline=True)
            embed.add_field(name="Задержка", value=f"{round(ctx.voice_client.latency * 1000)}ms", inline=True)
            embed.add_field(name="Участники", value=members_text[:1024], inline=False)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='voicelist', aliases=['vl'])
        async def voice_list(ctx):
            """Показывает список всех голосовых каналов сервера"""
            voice_channels = ctx.guild.voice_channels
            
            if not voice_channels:
                await ctx.send("❌ На сервере нет голосовых каналов!")
                return
            
            embed = discord.Embed(
                title=f"🎤 Голосовые каналы сервера {ctx.guild.name}",
                description=f"Всего каналов: **{len(voice_channels)}**",
                color=discord.Color.blue()
            )
            
            # Группируем по категориям
            categorized = {}
            for channel in voice_channels:
                category = channel.category.name if channel.category else "Без категории"
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(channel)
            
            for category, channels in categorized.items():
                channels_info = []
                for channel in channels:
                    members_count = len(channel.members)
                    limit = f"/{channel.user_limit}" if channel.user_limit > 0 else ""
                    bot_indicator = " 🤖" if ctx.voice_client and ctx.voice_client.channel == channel else ""
                    channels_info.append(f"• **{channel.name}** ({members_count}{limit}){bot_indicator}")
                
                embed.add_field(
                    name=f"📁 {category}",
                    value="\n".join(channels_info[:10]),  # Ограничиваем 10 каналами на категорию
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        # === КОМАНДА ПОМОЩИ ===
        
        @self.bot.command(name='help', aliases=['h', 'commands', 'команды'])
        async def help_command(ctx, command_name: str = None):
            """Показывает список всех команд или информацию о конкретной команде"""
            prefix = self.config.prefix
            
            if command_name:
                # Показываем информацию о конкретной команде
                cmd = self.bot.get_command(command_name)
                if not cmd:
                    await ctx.send(f"❌ Команда **{command_name}** не найдена!")
                    return
                
                embed = discord.Embed(
                    title=f"📖 Команда: {prefix}{cmd.name}",
                    description=cmd.help or "Описание отсутствует",
                    color=discord.Color.blue()
                )
                
                if cmd.aliases:
                    aliases = ", ".join([f"`{prefix}{alias}`" for alias in cmd.aliases])
                    embed.add_field(name="Альтернативные названия", value=aliases, inline=False)
                
                embed.add_field(name="Использование", value=f"`{prefix}{cmd.name} {cmd.signature}`", inline=False)
                
                await ctx.send(embed=embed)
                return
            
            # Показываем список всех команд
            embed = discord.Embed(
                title="📚 Список команд бота",
                description=f"Префикс команд: **{prefix}**\nДля подробной информации: `{prefix}help <команда>`",
                color=discord.Color.blue()
            )
            
            # Административные команды
            admin_commands = [
                f"`{prefix}setlogchannel <канал>` - Установить канал для логов",
                f"`{prefix}logstatus` - Показать статус логирования",
                f"`{prefix}togglelogs <тип>` - Включить/выключить тип логов",
                f"`{prefix}serverlist` - Список всех серверов бота",
                f"`{prefix}testlog` - Отправить тестовый лог"
            ]
            embed.add_field(name="🔧 Административные команды", value="\n".join(admin_commands), inline=False)
            
            # Голосовые команды
            voice_commands = [
                f"`{prefix}join` (или `{prefix}j`) - Подключиться к вашему голосовому каналу",
                f"`{prefix}leave` (или `{prefix}dc`) - Отключиться от голосового канала",
                f"`{prefix}move [канал]` (или `{prefix}mv`) - Переместиться в другой канал",
                f"`{prefix}voiceinfo` (или `{prefix}vi`) - Информация о текущем подключении",
                f"`{prefix}voicelist` (или `{prefix}vl`) - Список голосовых каналов"
            ]
            embed.add_field(name="🎤 Голосовые команды", value="\n".join(voice_commands), inline=False)
            
            # Общие команды
            general_commands = [
                f"`{prefix}botinfo` - Информация о боте",
                f"`{prefix}help [команда]` - Показать эту справку"
            ]
            embed.add_field(name="ℹ️ Общие команды", value="\n".join(general_commands), inline=False)
            
            embed.set_footer(text=f"Запрошено пользователем {ctx.author.name}")
            
            await ctx.send(embed=embed)