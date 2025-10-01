"""
Модуль для логирования событий Discord
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
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
            color=color
        )
        
        # Добавляем время в embed
        embed.add_field(name="🕐 Время", value=self.format_time(), inline=True)
        
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
            embed.set_footer(text=f"Сервер: {guild_id}")
            
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
    
    # === ЛОГИРОВАНИЕ СООБЩЕНИЙ ===
    async def log_message_create(self, message):
        """Логирует создание сообщения"""
        if not self.config.log_messages:
            return
        
        # Проверяем лимит частоты
        if self.is_rate_limited("message_create", message.author.id):
            return
        
        content = message.content[:1000] if message.content else "*Сообщение без текста*"
        
        await self.send_log(
            guild_id=message.guild.id,
            title="📝 Новое сообщение",
            description=f"**Автор:** {self.format_user_info(message.author)}\n**Канал:** {message.channel.mention}\n**Содержание:** {content}",
            color=discord.Color.green(),
            fields=[
                ("ID сообщения", str(message.id), True),
                ("Время создания", self.format_time(message.created_at), True),
                ("Вложения", f"{len(message.attachments)}" if message.attachments else "0", True)
            ],
            thumbnail=message.author.display_avatar.url
        )
    
    async def log_message_edit(self, before, after):
        """Логирует редактирование сообщения"""
        if not self.config.log_messages or before.content == after.content:
            return
        
        # Проверяем лимит частоты
        if self.is_rate_limited("message_edit", after.author.id):
            return
        
        old_content = before.content[:500] if before.content else "*Пустое сообщение*"
        new_content = after.content[:500] if after.content else "*Пустое сообщение*"
        
        await self.send_log(
            guild_id=after.guild.id,
            title="✏️ Сообщение отредактировано",
            description=f"**Автор:** {self.format_user_info(after.author)}\n**Канал:** {after.channel.mention}",
            color=discord.Color.orange(),
            fields=[
                ("Старое содержимое", old_content, False),
                ("Новое содержимое", new_content, False),
                ("ID сообщения", str(after.id), True),
                ("Время редактирования", self.format_time(after.edited_at) if after.edited_at else "Неизвестно", True)
            ],
            thumbnail=after.author.display_avatar.url
        )
    
    async def log_message_delete(self, message):
        """Логирует удаление сообщения"""
        if not self.config.log_messages:
            return
        
        # Проверяем лимит частоты
        if self.is_rate_limited("message_delete", message.author.id):
            return
        
        content = message.content[:1000] if message.content else "*Сообщение без текста*"
        
        await self.send_log(
            guild_id=message.guild.id,
            title="🗑️ Сообщение удалено",
            description=f"**Автор:** {self.format_user_info(message.author)}\n**Канал:** {message.channel.mention}\n**Содержание:** {content}",
            color=discord.Color.red(),
            fields=[
                ("ID сообщения", str(message.id), True),
                ("Время создания", self.format_time(message.created_at), True),
                ("Время удаления", self.format_time(), True)
            ],
            thumbnail=message.author.display_avatar.url
        )
    
    async def log_bulk_message_delete(self, messages):
        """Логирует массовое удаление сообщений"""
        if not self.config.log_messages:
            return
        
        # Группируем по авторам
        authors = {}
        for message in messages:
            author_id = message.author.id
            if author_id not in authors:
                authors[author_id] = {
                    'user': message.author,
                    'count': 0
                }
            authors[author_id]['count'] += 1
        
        # Отправляем лог для каждого автора
        for author_data in authors.values():
            user = author_data['user']
            count = author_data['count']
            
            await self.send_log(
                guild_id=messages[0].guild.id,
                title="🗑️ Массовое удаление сообщений",
                description=f"**Автор:** {self.format_user_info(user)}\n**Канал:** {messages[0].channel.mention}\n**Количество удаленных сообщений:** {count}",
                color=discord.Color.dark_red(),
                fields=[
                    ("Время удаления", self.format_time(), True),
                    ("Всего удалено", str(len(messages)), True)
                ],
                thumbnail=user.display_avatar.url
            )
    
    # === ЛОГИРОВАНИЕ УЧАСТНИКОВ ===
    async def log_member_join(self, member):
        """Логирует присоединение участника"""
        if not self.config.log_members:
            return
        
        account_age = datetime.utcnow() - member.created_at
        days_old = account_age.days
        
        fields = [
            ("ID пользователя", str(member.id), True),
            ("Возраст аккаунта", f"{days_old} дней", True),
            ("Участников на сервере", str(member.guild.member_count), True)
        ]
        
        if member.pending:
            fields.append(("Статус", "Ожидает проверки правил", True))
        
        await self.send_log(
            guild_id=member.guild.id,
            title="👋 Участник присоединился",
            description=f"**Пользователь:** {self.format_user_info(member)}",
            color=discord.Color.green(),
            fields=fields,
            thumbnail=member.display_avatar.url
        )
    
    async def log_member_remove(self, member):
        """Логирует выход участника"""
        if not self.config.log_members:
            return
        
        # Получаем роли участника
        roles = [role.mention for role in member.roles[1:]]  # Исключаем @everyone
        roles_text = ", ".join(roles) if roles else "Без ролей"
        
        await self.send_log(
            guild_id=member.guild.id,
            title="👋 Участник покинул сервер",
            description=f"**Пользователь:** {self.format_user_info(member)}",
            color=discord.Color.red(),
            fields=[
                ("Роли", roles_text[:1000], False),
                ("Участников на сервере", str(member.guild.member_count), True),
                ("Время на сервере", f"{(datetime.utcnow() - member.joined_at).days} дней" if member.joined_at else "Неизвестно", True)
            ],
            thumbnail=member.display_avatar.url
        )
    
    async def log_member_update(self, before, after):
        """Логирует обновление участника"""
        if not self.config.log_members:
            return
        
        changes = []
        
        # Проверяем изменения никнейма
        if before.display_name != after.display_name:
            changes.append(("📝 Никнейм", f"{before.display_name} → {after.display_name}", False))
        
        # Проверяем изменения ролей
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles:
                roles_text = ", ".join([role.mention for role in added_roles])
                changes.append(("➕ Добавлены роли", roles_text, False))
            
            if removed_roles:
                roles_text = ", ".join([role.mention for role in removed_roles])
                changes.append(("➖ Удалены роли", roles_text, False))
        
        # Проверяем изменения аватара
        if before.display_avatar.url != after.display_avatar.url:
            changes.append(("🖼️ Аватар", "Изменен", True))
        
        # Проверяем изменения статуса проверки правил
        if hasattr(before, 'pending') and hasattr(after, 'pending') and before.pending != after.pending:
            status = "✅ Прошел проверку" if not after.pending else "⏳ Ожидает проверки"
            changes.append(("📋 Статус проверки", status, True))
        
        if changes:
            fields = [("ID пользователя", str(after.id), True)]
            fields.extend(changes)
            
            await self.send_log(
                guild_id=after.guild.id,
                title="👤 Профиль участника обновлен",
                description=f"**Пользователь:** {self.format_user_info(after)}",
                color=discord.Color.blue(),
                fields=fields,
                thumbnail=after.display_avatar.url
            )
    
    async def log_user_update(self, before, after):
        """Логирует обновление пользователя"""
        if not self.config.log_members:
            return
        
        changes = []
        
        # Проверяем изменения имени пользователя
        if before.name != after.name:
            changes.append(("👤 Имя пользователя", f"{before.name} → {after.name}", False))
        
        # Проверяем изменения дискриминатора
        if before.discriminator != after.discriminator:
            changes.append(("🏷️ Дискриминатор", f"{before.discriminator} → {after.discriminator}", False))
        
        # Проверяем изменения аватара
        if before.avatar.url != after.avatar.url:
            changes.append(("🖼️ Аватар", "Изменен", True))
        
        if changes:
            fields = [("ID пользователя", str(after.id), True)]
            fields.extend(changes)
            
            # Отправляем в каналы логов всех серверов, где есть этот пользователь
            for guild in self.bot.guilds:
                if guild.get_member(after.id):
                    await self.send_log(
                        guild_id=guild.id,
                        title="👤 Профиль пользователя обновлен",
                        description=f"**Пользователь:** {self.format_user_info(after)}",
                        color=discord.Color.blue(),
                        fields=fields,
                        thumbnail=after.display_avatar.url
                    )
    
    # === ЛОГИРОВАНИЕ КАНАЛОВ ===
    async def log_channel_create(self, channel):
        """Логирует создание канала"""
        if not self.config.log_channels:
            return
        
        channel_type = self.get_channel_type_emoji(channel.type)
        category = f" в категории {channel.category.name}" if channel.category else ""
        
        fields = [
            ("ID канала", str(channel.id), True),
            ("Тип", channel.type.name, True),
            ("Позиция", str(channel.position), True)
        ]
        
        if hasattr(channel, 'topic') and channel.topic:
            fields.append(("Описание", channel.topic[:500], False))
        
        await self.send_log(
            guild_id=channel.guild.id,
            title=f"{channel_type} Канал создан",
            description=f"**Канал:** {channel.mention}{category}",
            color=discord.Color.green(),
            fields=fields
        )
    
    async def log_channel_delete(self, channel):
        """Логирует удаление канала"""
        if not self.config.log_channels:
            return
        
        channel_type = self.get_channel_type_emoji(channel.type)
        category = f" из категории {channel.category.name}" if channel.category else ""
        
        fields = [
            ("Название", channel.name, True),
            ("Тип", channel.type.name, True),
            ("ID канала", str(channel.id), True)
        ]
        
        if hasattr(channel, 'topic') and channel.topic:
            fields.append(("Описание", channel.topic[:500], False))
        
        await self.send_log(
            guild_id=channel.guild.id,
            title=f"{channel_type} Канал удален",
            description=f"**Канал:** #{channel.name}{category}",
            color=discord.Color.red(),
            fields=fields
        )
    
    async def log_channel_update(self, before, after):
        """Логирует обновление канала"""
        if not self.config.log_channels:
            return
        
        changes = []
        
        # Проверяем изменения названия
        if before.name != after.name:
            changes.append(("📝 Название", f"{before.name} → {after.name}", False))
        
        # Проверяем изменения описания
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            old_topic = before.topic[:200] if before.topic else "*Без описания*"
            new_topic = after.topic[:200] if after.topic else "*Без описания*"
            changes.append(("📄 Описание", f"{old_topic} → {new_topic}", False))
        
        # Проверяем изменения категории
        if before.category != after.category:
            old_category = before.category.name if before.category else "Без категории"
            new_category = after.category.name if after.category else "Без категории"
            changes.append(("📁 Категория", f"{old_category} → {new_category}", False))
        
        # Проверяем изменения позиции
        if before.position != after.position:
            changes.append(("📍 Позиция", f"{before.position} → {after.position}", True))
        
        if changes:
            fields = [("ID канала", str(after.id), True)]
            fields.extend(changes)
            
            await self.send_log(
                guild_id=after.guild.id,
                title="📝 Канал обновлен",
                description=f"**Канал:** {after.mention}",
                color=discord.Color.blue(),
                fields=fields
            )
    
    # === ЛОГИРОВАНИЕ РОЛЕЙ ===
    async def log_role_create(self, role):
        """Логирует создание роли"""
        if not self.config.log_roles:
            return
        
        fields = [
            ("ID роли", str(role.id), True),
            ("Цвет", f"#{role.color.value:06x}", True),
            ("Позиция", str(role.position), True),
            ("Отдельно показывать", "✅" if role.hoist else "❌", True),
            ("Упоминаемая", "✅" if role.mentionable else "❌", True),
            ("Управляемая ботом", "✅" if role.managed else "❌", True)
        ]
        
        if role.permissions.value != 0:
            fields.append(("Разрешения", f"{role.permissions.value}", False))
        
        await self.send_log(
            guild_id=role.guild.id,
            title="🎭 Роль создана",
            description=f"**Роль:** {role.mention}",
            color=role.color if role.color.value != 0 else discord.Color.blue(),
            fields=fields
        )
    
    async def log_role_delete(self, role):
        """Логирует удаление роли"""
        if not self.config.log_roles:
            return
        
        fields = [
            ("Название", role.name, True),
            ("ID роли", str(role.id), True),
            ("Участников с ролью", str(len(role.members)), True),
            ("Позиция", str(role.position), True)
        ]
        
        await self.send_log(
            guild_id=role.guild.id,
            title="🎭 Роль удалена",
            description=f"**Роль:** @{role.name}",
            color=discord.Color.red(),
            fields=fields
        )
    
    async def log_role_update(self, before, after):
        """Логирует обновление роли"""
        if not self.config.log_roles:
            return
        
        changes = []
        
        # Проверяем изменения названия
        if before.name != after.name:
            changes.append(("📝 Название", f"{before.name} → {after.name}", False))
        
        # Проверяем изменения цвета
        if before.color != after.color:
            old_color = f"#{before.color.value:06x}"
            new_color = f"#{after.color.value:06x}"
            changes.append(("🎨 Цвет", f"{old_color} → {new_color}", True))
        
        # Проверяем изменения позиции
        if before.position != after.position:
            changes.append(("📍 Позиция", f"{before.position} → {after.position}", True))
        
        # Проверяем изменения разрешений
        if before.permissions != after.permissions:
            old_perms = before.permissions.value
            new_perms = after.permissions.value
            changes.append(("🔐 Разрешения", f"{old_perms} → {new_perms}", False))
        
        # Проверяем изменения флагов
        if before.hoist != after.hoist:
            status = "✅" if after.hoist else "❌"
            changes.append(("📋 Отдельно показывать", status, True))
        
        if before.mentionable != after.mentionable:
            status = "✅" if after.mentionable else "❌"
            changes.append(("💬 Упоминаемая", status, True))
        
        if changes:
            fields = [("ID роли", str(after.id), True)]
            fields.extend(changes)
            
            await self.send_log(
                guild_id=after.guild.id,
                title="🎭 Роль обновлена",
                description=f"**Роль:** {after.mention}",
                color=after.color if after.color.value != 0 else discord.Color.blue(),
                fields=fields
            )
    
    # === ЛОГИРОВАНИЕ РЕАКЦИЙ ===
    async def log_reaction_add(self, reaction, user):
        """Логирует добавление реакции"""
        # Проверяем лимит частоты
        if self.is_rate_limited("reaction_add", user.id):
            return
        
        await self.send_log(
            guild_id=reaction.message.guild.id,
            title="👍 Реакция добавлена",
            description=f"**Пользователь:** {self.format_user_info(user)}\n**Канал:** {reaction.message.channel.mention}",
            color=discord.Color.green(),
            fields=[
                ("Реакция", str(reaction.emoji), True),
                ("Количество", str(reaction.count), True),
                ("ID сообщения", str(reaction.message.id), True),
                ("Ссылка на сообщение", f"[Перейти]({reaction.message.jump_url})", False)
            ],
            thumbnail=user.display_avatar.url
        )
    
    async def log_reaction_remove(self, reaction, user):
        """Логирует удаление реакции"""
        # Проверяем лимит частоты
        if self.is_rate_limited("reaction_remove", user.id):
            return
        
        await self.send_log(
            guild_id=reaction.message.guild.id,
            title="👎 Реакция удалена",
            description=f"**Пользователь:** {self.format_user_info(user)}\n**Канал:** {reaction.message.channel.mention}",
            color=discord.Color.red(),
            fields=[
                ("Реакция", str(reaction.emoji), True),
                ("Количество", str(reaction.count), True),
                ("ID сообщения", str(reaction.message.id), True),
                ("Ссылка на сообщение", f"[Перейти]({reaction.message.jump_url})", False)
            ],
            thumbnail=user.display_avatar.url
        )
    
    async def log_reaction_clear(self, message, reactions):
        """Логирует очистку всех реакций"""
        reactions_text = ", ".join([str(r.emoji) for r in reactions]) if reactions else "Нет реакций"
        
        await self.send_log(
            guild_id=message.guild.id,
            title="🧹 Все реакции очищены",
            description=f"**Канал:** {message.channel.mention}",
            color=discord.Color.orange(),
            fields=[
                ("Очищенные реакции", reactions_text[:1000], False),
                ("ID сообщения", str(message.id), True),
                ("Ссылка на сообщение", f"[Перейти]({message.jump_url})", False)
            ]
        )
    
    # === ЛОГИРОВАНИЕ ГОЛОСОВЫХ КАНАЛОВ ===
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
                    ("Участников в канале", str(len(after.channel.members)), True)
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
    
    # === ЛОГИРОВАНИЕ СЕРВЕРА ===
    async def log_guild_update(self, before, after):
        """Логирует обновление сервера"""
        changes = []
        
        # Проверяем изменения названия
        if before.name != after.name:
            changes.append(("📝 Название", f"{before.name} → {after.name}", False))
        
        # Проверяем изменения описания
        if before.description != after.description:
            old_desc = before.description[:200] if before.description else "*Без описания*"
            new_desc = after.description[:200] if after.description else "*Без описания*"
            changes.append(("📄 Описание", f"{old_desc} → {new_desc}", False))
        
        # Проверяем изменения иконки
        if before.icon != after.icon:
            changes.append(("🖼️ Иконка", "Изменена", True))
        
        # Проверяем изменения баннера
        if before.banner != after.banner:
            changes.append(("🖼️ Баннер", "Изменен", True))
        
        # Проверяем изменения уровня проверки
        if before.verification_level != after.verification_level:
            changes.append(("🔐 Уровень проверки", f"{before.verification_level.name} → {after.verification_level.name}", True))
        
        # Проверяем изменения уровня уведомлений
        if before.default_notifications != after.default_notifications:
            changes.append(("🔔 Уведомления", f"{before.default_notifications.name} → {after.default_notifications.name}", True))
        
        if changes:
            fields = [("ID сервера", str(after.id), True)]
            fields.extend(changes)
            
            await self.send_log(
                guild_id=after.id,
                title="🏰 Сервер обновлен",
                description=f"**Сервер:** {after.name}",
                color=discord.Color.blue(),
                fields=fields
            )
    
    async def log_guild_emojis_update(self, guild, before, after):
        """Логирует обновление эмодзи сервера"""
        added = [emoji for emoji in after if emoji not in before]
        removed = [emoji for emoji in before if emoji not in after]
        
        if added:
            emojis_text = ", ".join([str(emoji) for emoji in added])
            await self.send_log(
                guild_id=guild.id,
                title="😀 Эмодзи добавлены",
                description=f"**Сервер:** {guild.name}",
                color=discord.Color.green(),
                fields=[
                    ("Добавленные эмодзи", emojis_text[:1000], False),
                    ("Количество", str(len(added)), True)
                ]
            )
        
        if removed:
            emojis_text = ", ".join([str(emoji) for emoji in removed])
            await self.send_log(
                guild_id=guild.id,
                title="😀 Эмодзи удалены",
                description=f"**Сервер:** {guild.name}",
                color=discord.Color.red(),
                fields=[
                    ("Удаленные эмодзи", emojis_text[:1000], False),
                    ("Количество", str(len(removed)), True)
                ]
            )
    
    async def log_guild_stickers_update(self, guild, before, after):
        """Логирует обновление стикеров сервера"""
        added = [sticker for sticker in after if sticker not in before]
        removed = [sticker for sticker in before if sticker not in after]
        
        if added:
            stickers_text = ", ".join([sticker.name for sticker in added])
            await self.send_log(
                guild_id=guild.id,
                title="🎨 Стикеры добавлены",
                description=f"**Сервер:** {guild.name}",
                color=discord.Color.green(),
                fields=[
                    ("Добавленные стикеры", stickers_text[:1000], False),
                    ("Количество", str(len(added)), True)
                ]
            )
        
        if removed:
            stickers_text = ", ".join([sticker.name for sticker in removed])
            await self.send_log(
                guild_id=guild.id,
                title="🎨 Стикеры удалены",
                description=f"**Сервер:** {guild.name}",
                color=discord.Color.red(),
                fields=[
                    ("Удаленные стикеры", stickers_text[:1000], False),
                    ("Количество", str(len(removed)), True)
                ]
            )
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def get_channel_type_emoji(self, channel_type):
        """Возвращает эмодзи для типа канала"""
        emoji_map = {
            discord.ChannelType.text: "💬",
            discord.ChannelType.voice: "🔊",
            discord.ChannelType.category: "📁",
            discord.ChannelType.news: "📢",
            discord.ChannelType.stage_voice: "🎭",
            discord.ChannelType.forum: "📋"
        }
        return emoji_map.get(channel_type, "❓")
    
    def format_time(self, dt=None):
        """Форматирует время для отображения в UTC+7 (Новосибирское)"""
        if dt is None:
            dt = datetime.utcnow()
        
        # Конвертируем в UTC+7 (Новосибирское время)
        novosibirsk_tz = timezone(timedelta(hours=7))
        if dt.tzinfo is None:
            # Если время без timezone, считаем его UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        local_time = dt.astimezone(novosibirsk_tz)
        return local_time.strftime('%d.%m.%Y %H:%M:%S MSK+4')
