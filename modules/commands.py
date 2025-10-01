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
    def __init__(self, bot, config, discord_logger, speech_recognizer, voice_recorder=None):
        self.bot = bot
        self.config = config
        self.discord_logger = discord_logger
        self.speech_recognizer = speech_recognizer
        self.voice_recorder = voice_recorder
    
    def setup_commands(self):
        """Настраивает команды бота"""
        
        @self.bot.command(name='setlogchannel')
        @commands.has_permissions(administrator=True)
        async def set_log_channel(ctx, channel: discord.TextChannel):
            """Устанавливает канал для логов на текущем сервере"""
            self.config.set_log_channel_id(ctx.guild.id, channel.id)
            
            await ctx.send(f"✅ Канал для логов установлен: {channel.mention}\n"
                          f"Теперь все логи сервера **{ctx.guild.name}** будут отправляться в этот канал!")
        
        @self.bot.command(name='excludeuser')
        @commands.has_permissions(administrator=True)
        async def exclude_user(ctx, user: discord.Member):
            """Исключает пользователя из распознавания речи"""
            self.config.add_excluded_user(ctx.guild.id, user.id)
            
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title="🚫 Пользователь исключен из распознавания речи",
                description=f"**Пользователь:** {self.discord_logger.format_user_info(user)}\n**Исключил:** {ctx.author.mention}",
                color=discord.Color.orange(),
                fields=[
                    ("Время исключения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                ],
                thumbnail=user.display_avatar.url
            )
            
            await ctx.send(f"✅ Пользователь {user.mention} исключен из распознавания речи!")
        
        @self.bot.command(name='includeuser')
        @commands.has_permissions(administrator=True)
        async def include_user(ctx, user: discord.Member):
            """Включает пользователя в распознавание речи"""
            self.config.remove_excluded_user(ctx.guild.id, user.id)
            
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title="✅ Пользователь включен в распознавание речи",
                description=f"**Пользователь:** {self.discord_logger.format_user_info(user)}\n**Включил:** {ctx.author.mention}",
                color=discord.Color.green(),
                fields=[
                    ("Время включения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                ],
                thumbnail=user.display_avatar.url
            )
            
            await ctx.send(f"✅ Пользователь {user.mention} включен в распознавание речи!")
        
        @self.bot.command(name='excludedusers')
        @commands.has_permissions(administrator=True)
        async def excluded_users(ctx):
            """Показывает список исключенных пользователей"""
            excluded = self.config.excluded_users.get(ctx.guild.id, set())
            
            if not excluded:
                await ctx.send("❌ Нет исключенных пользователей на этом сервере.")
                return
            
            embed = discord.Embed(
                title="🚫 Исключенные пользователи",
                description=f"**Сервер:** {ctx.guild.name}",
                color=discord.Color.orange()
            )
            
            users_list = []
            for user_id in excluded:
                user = ctx.guild.get_member(user_id)
                if user:
                    users_list.append(f"• {user.mention} (`{user_id}`)")
                else:
                    users_list.append(f"• Неизвестный пользователь (`{user_id}`)")
            
            embed.add_field(
                name="Исключенные пользователи",
                value="\n".join(users_list[:20]) + ("..." if len(users_list) > 20 else ""),
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='togglespeech')
        @commands.has_permissions(administrator=True)
        async def toggle_speech_recognition(ctx):
            """Включает/выключает распознавание речи"""
            self.config.speech_recognition = not self.config.speech_recognition
            self.config.save_config()
            
            status = "включено" if self.config.speech_recognition else "выключено"
            
            await self.discord_logger.send_log(
                guild_id=ctx.guild.id,
                title="🎤 Распознавание речи изменено",
                description=f"**Статус:** {status.title()}\n**Изменил:** {ctx.author.mention}",
                color=discord.Color.blue() if self.config.speech_recognition else discord.Color.red(),
                fields=[
                    ("Время изменения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                ]
            )
            
            await ctx.send(f"✅ Распознавание речи {status}!")
        
        @self.bot.command(name='joinvoice')
        @commands.has_permissions(administrator=True)
        async def join_voice(ctx, *, channel: discord.VoiceChannel = None):
            """Подключает бота к голосовому каналу с записью голоса"""
            if not channel:
                if ctx.author.voice and ctx.author.voice.channel:
                    channel = ctx.author.voice.channel
                else:
                    await ctx.send("❌ Укажите голосовой канал или подключитесь к голосовому каналу!")
                    return
            
            try:
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect()
                
                # Подключаемся к каналу
                voice_client = await channel.connect()
                
                # Начинаем запись голоса
                if self.voice_recorder and self.config.speech_recognition:
                    await self.voice_recorder.start_recording(voice_client, ctx.guild.id)
                    recording_status = "✅ Запись активна"
                else:
                    recording_status = "❌ Запись недоступна"
                
                await self.discord_logger.send_log(
                    guild_id=ctx.guild.id,
                    title="🎤 Бот подключен к голосовому каналу",
                    description=f"**Канал:** {channel.mention}\n**Подключил:** {ctx.author.mention}",
                    color=discord.Color.green(),
                    fields=[
                        ("Участников в канале", str(len(channel.members)), True),
                        ("Распознавание речи", "✅ Включено" if self.config.speech_recognition else "❌ Выключено", True),
                        ("Запись голоса", recording_status, True),
                        ("Язык", self.config.speech_language, True),
                        ("FFmpeg", "✅ Установлен", True)
                    ]
                )
                
                await ctx.send(f"✅ Бот подключен к голосовому каналу {channel.mention}!\n"
                              f"🎤 Распознавание речи: {'Включено' if self.config.speech_recognition else 'Выключено'}\n"
                              f"🎙️ Запись голоса: {recording_status}\n"
                              f"🌍 Язык: {self.config.speech_language}\n"
                              f"🎬 FFmpeg: Установлен")
                
            except Exception as e:
                await ctx.send(f"❌ Ошибка подключения к голосовому каналу: {e}")
                logger.error(f"Ошибка подключения к голосовому каналу: {e}")
        
        @self.bot.command(name='leavevoice')
        @commands.has_permissions(administrator=True)
        async def leave_voice(ctx):
            """Отключает бота от голосового канала"""
            if not ctx.guild.voice_client:
                await ctx.send("❌ Бот не подключен к голосовому каналу!")
                return
            
            try:
                channel = ctx.guild.voice_client.channel
                
                # Останавливаем запись голоса
                if self.voice_recorder:
                    await self.voice_recorder.stop_recording(ctx.guild.id)
                
                await ctx.guild.voice_client.disconnect()
                
                await self.discord_logger.send_log(
                    guild_id=ctx.guild.id,
                    title="🎤 Бот отключен от голосового канала",
                    description=f"**Канал:** {channel.mention}\n**Отключил:** {ctx.author.mention}",
                    color=discord.Color.red(),
                    fields=[
                        ("Время отключения", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                    ]
                )
                
                await ctx.send("✅ Бот отключен от голосового канала!")
                
            except Exception as e:
                await ctx.send(f"❌ Ошибка отключения от голосового канала: {e}")
                logger.error(f"Ошибка отключения от голосового канала: {e}")
        
        @self.bot.command(name='voicefiles')
        @commands.has_permissions(administrator=True)
        async def voice_files(ctx):
            """Показывает информацию о файлах с распознанной речью"""
            stats = await self.speech_recognizer.get_voice_logs_stats(ctx.guild.id)
            
            if not stats['exists']:
                await ctx.send("❌ Файл с распознанной речью не найден!")
                return
            
            embed = discord.Embed(
                title="📁 Файлы с распознанной речью",
                description=f"**Сервер:** {ctx.guild.name}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Файл", value=f"`voice_logs_{ctx.guild.id}/voice.txt`", inline=False)
            embed.add_field(name="Размер", value=f"{stats['size'] / 1024:.1f} KB", inline=True)
            embed.add_field(name="Записей", value=str(stats['lines']), inline=True)
            embed.add_field(name="Язык", value=self.config.speech_language, inline=True)
            
            # Показываем последние записи
            if stats['recent_lines']:
                recent_text = "".join(stats['recent_lines'])
                if len(recent_text) > 1000:
                    recent_text = recent_text[:997] + "..."
                
                embed.add_field(
                    name="Последние записи",
                    value=f"```\n{recent_text}\n```",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='clearspeech')
        @commands.has_permissions(administrator=True)
        async def clear_speech_logs(ctx):
            """Очищает файл с распознанной речью"""
            success = self.speech_recognizer.clear_voice_logs(ctx.guild.id)
            
            if success:
                await self.discord_logger.send_log(
                    guild_id=ctx.guild.id,
                    title="🗑️ Файл с речью очищен",
                    description=f"**Очистил:** {ctx.author.mention}",
                    color=discord.Color.red(),
                    fields=[
                        ("Время очистки", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                    ]
                )
                
                await ctx.send("✅ Файл с распознанной речью очищен!")
            else:
                await ctx.send("❌ Файл с распознанной речью не найден!")
        
        @self.bot.command(name='speechstatus')
        @commands.has_permissions(administrator=True)
        async def speech_status(ctx):
            """Показывает статус распознавания речи"""
            embed = discord.Embed(
                title="🎤 Статус распознавания речи",
                color=discord.Color.blue()
            )
            
            status_emoji = "✅" if self.config.speech_recognition else "❌"
            embed.add_field(name="Распознавание речи", value=f"{status_emoji} {'Включено' if self.config.speech_recognition else 'Выключено'}", inline=True)
            embed.add_field(name="Язык", value=self.config.speech_language, inline=True)
            embed.add_field(name="Минимальная длительность", value=f"{self.config.min_audio_duration}с", inline=True)
            embed.add_field(name="Максимальная длительность", value=f"{self.config.max_audio_duration}с", inline=True)
            
            excluded_count = len(self.config.excluded_users.get(ctx.guild.id, set()))
            embed.add_field(name="Исключенных пользователей", value=str(excluded_count), inline=True)
            
            # Проверяем FFmpeg
            from modules.ffmpeg_setup import check_ffmpeg
            ffmpeg_status = "✅ Установлен" if check_ffmpeg() else "❌ Не установлен"
            embed.add_field(name="FFmpeg", value=ffmpeg_status, inline=True)
            
            # Статус записи голоса
            if self.voice_recorder:
                recording_status = "✅ Активна" if self.voice_recorder.is_recording(ctx.guild.id) else "❌ Неактивна"
                embed.add_field(name="Запись голоса", value=recording_status, inline=True)
            else:
                embed.add_field(name="Запись голоса", value="❌ Недоступна", inline=True)
            
            # Информация о файле логов
            stats = await self.speech_recognizer.get_voice_logs_stats(ctx.guild.id)
            
            if stats['exists']:
                embed.add_field(name="Файл логов", value=f"`voice_logs_{ctx.guild.id}/voice.txt`", inline=False)
                embed.add_field(name="Размер файла", value=f"{stats['size'] / 1024:.1f} KB", inline=True)
                embed.add_field(name="Записей", value=str(stats['lines']), inline=True)
            else:
                embed.add_field(name="Файл логов", value="❌ Не создан", inline=False)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='startrecording')
        @commands.has_permissions(administrator=True)
        async def start_recording(ctx):
            """Начинает запись голоса в текущем голосовом канале"""
            if not ctx.guild.voice_client:
                await ctx.send("❌ Бот не подключен к голосовому каналу!")
                return
            
            if not self.voice_recorder:
                await ctx.send("❌ Модуль записи голоса недоступен!")
                return
            
            if self.voice_recorder.is_recording(ctx.guild.id):
                await ctx.send("❌ Запись голоса уже активна!")
                return
            
            try:
                success = await self.voice_recorder.start_recording(ctx.guild.voice_client, ctx.guild.id)
                
                if success:
                    await self.discord_logger.send_log(
                        guild_id=ctx.guild.id,
                        title="🎙️ Запись голоса начата",
                        description=f"**Начал:** {ctx.author.mention}",
                        color=discord.Color.green(),
                        fields=[
                            ("Время начала", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                        ]
                    )
                    
                    await ctx.send("✅ Запись голоса начата! Бот теперь слышит и распознает речь.")
                else:
                    await ctx.send("❌ Ошибка начала записи голоса!")
                    
            except Exception as e:
                await ctx.send(f"❌ Ошибка начала записи голоса: {e}")
                logger.error(f"Ошибка начала записи голоса: {e}")
        
        @self.bot.command(name='stoprecording')
        @commands.has_permissions(administrator=True)
        async def stop_recording(ctx):
            """Останавливает запись голоса"""
            if not self.voice_recorder:
                await ctx.send("❌ Модуль записи голоса недоступен!")
                return
            
            if not self.voice_recorder.is_recording(ctx.guild.id):
                await ctx.send("❌ Запись голоса не активна!")
                return
            
            try:
                success = await self.voice_recorder.stop_recording(ctx.guild.id)
                
                if success:
                    await self.discord_logger.send_log(
                        guild_id=ctx.guild.id,
                        title="🎙️ Запись голоса остановлена",
                        description=f"**Остановил:** {ctx.author.mention}",
                        color=discord.Color.red(),
                        fields=[
                            ("Время остановки", datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S'), True)
                        ]
                    )
                    
                    await ctx.send("✅ Запись голоса остановлена!")
                else:
                    await ctx.send("❌ Ошибка остановки записи голоса!")
                    
            except Exception as e:
                await ctx.send(f"❌ Ошибка остановки записи голоса: {e}")
                logger.error(f"Ошибка остановки записи голоса: {e}")
        
        @self.bot.command(name='testrecognition')
        @commands.has_permissions(administrator=True)
        async def test_recognition(ctx, *, audio_file_path: str = None):
            """Тестирует распознавание речи на аудио файле"""
            if not audio_file_path:
                await ctx.send("❌ Укажите путь к аудио файлу!\n"
                              "Пример: `!testrecognition test_audio.wav`")
                return
            
            if not os.path.exists(audio_file_path):
                await ctx.send(f"❌ Файл не найден: `{audio_file_path}`")
                return
            
            await ctx.send("🔄 Тестирую распознавание речи...")
            
            try:
                text = await self.speech_recognizer.test_recognition(audio_file_path)
                
                if text:
                    embed = discord.Embed(
                        title="✅ Тест распознавания речи успешен",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Файл", value=f"`{audio_file_path}`", inline=False)
                    embed.add_field(name="Распознанный текст", value=text, inline=False)
                    embed.add_field(name="Язык", value=self.config.speech_language, inline=True)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Не удалось распознать речь в файле. Проверьте:\n"
                                  "• Поддерживаемый формат аудио (WAV, MP3, M4A)\n"
                                  "• Длительность аудио (0.5-30 секунд)\n"
                                  "• Качество записи\n"
                                  "• Язык речи")
                    
            except Exception as e:
                await ctx.send(f"❌ Ошибка тестирования: {e}")
                logger.error(f"Ошибка тестирования распознавания речи: {e}")
        
        @self.bot.command(name='simulatevoice')
        @commands.has_permissions(administrator=True)
        async def simulate_voice(ctx, *, text: str = None):
            """Симулирует распознавание речи (для демонстрации)"""
            if not text:
                await ctx.send("❌ Укажите текст для симуляции!\n"
                              "Пример: `!simulatevoice Привет, как дела?`")
                return
            
            if not self.voice_recorder:
                await ctx.send("❌ Модуль записи голоса недоступен!")
                return
            
            try:
                # Симулируем распознавание речи
                await self.voice_recorder.simulate_voice_recognition(
                    ctx.guild.id, ctx.author.id, text
                )
                
                await ctx.send(f"✅ Симулированная речь записана: **{text}**\n"
                              f"Проверьте файл логов командой `!voicefiles`")
                
            except Exception as e:
                await ctx.send(f"❌ Ошибка симуляции: {e}")
                logger.error(f"Ошибка симуляции голоса: {e}")
        
        @self.bot.command(name='botinfo')
        async def bot_info(ctx):
            """Информация о боте"""
            embed = discord.Embed(
                title="🤖 Информация о боте",
                color=discord.Color.blue()
            )
            embed.add_field(name="Версия", value="6.0.0 (Modular Speech Bot)", inline=True)
            embed.add_field(name="Фреймворк", value="Disnake 2.9.0+", inline=True)
            embed.add_field(name="Серверов", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="Пользователей", value=len(self.bot.users), inline=True)
            
            channel_id = self.config.get_log_channel_id(ctx.guild.id)
            channel_info = f"<#{channel_id}>" if channel_id else "Не установлен"
            embed.add_field(name="Канал логов", value=channel_info, inline=False)
            
            # Информация о голосовом подключении
            if ctx.guild.voice_client:
                voice_channel = ctx.guild.voice_client.channel
                voice_info = f"🔊 {voice_channel.mention}"
            else:
                voice_info = "❌ Не подключен"
            
            embed.add_field(name="Голосовое подключение", value=voice_info, inline=False)
            
            # Информация о распознавании речи
            speech_info = f"🎤 {'Включено' if self.config.speech_recognition else 'Выключено'} ({self.config.speech_language})"
            embed.add_field(name="Распознавание речи", value=speech_info, inline=False)
            
            # Проверяем FFmpeg
            from modules.ffmpeg_setup import check_ffmpeg
            ffmpeg_info = "✅ Установлен" if check_ffmpeg() else "❌ Не установлен"
            embed.add_field(name="FFmpeg", value=ffmpeg_info, inline=True)
            
            embed.add_field(name="Префикс", value=self.config.prefix, inline=True)
            embed.add_field(name="Задержка", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
            
            await ctx.send(embed=embed)
