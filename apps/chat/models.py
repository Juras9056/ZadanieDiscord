from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password


class Channel(models.Model):
    class ChannelType(models.TextChoices):
        PUBLIC = 'public', 'Publiczny'
        PRIVATE = 'private', 'Prywatny'

    class SubType(models.TextChoices):
        TEXT = 'text', 'Tekstowy'
        VOICE = 'voice', 'Głosowy'

    # Top-level channels = "servers". Sub-channels have parent set.
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='sub_channels'
    )
    # 'text' or 'voice' — only for sub-channels; null for top-level servers
    sub_type = models.CharField(
        max_length=10, choices=SubType.choices, null=True, blank=True
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    channel_type = models.CharField(
        max_length=10, choices=ChannelType.choices, default=ChannelType.PUBLIC
    )
    # Hashed password for private top-level channels
    password = models.CharField(max_length=128, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_channels'
    )
    # Members tracked on top-level channels; sub-channels inherit from parent
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='channels', blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'parent']]

    def __str__(self):
        if self.parent:
            return f'#{self.parent.name} / {self.sub_type}:{self.name}'
        return f'#{self.name}'

    def is_server(self):
        """Top-level channel (Discord "server")."""
        return self.parent_id is None

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_members(self):
        """Members of sub-channels come from the parent server."""
        return self.parent.members if self.parent_id else self.members

    def get_membership(self, user):
        """Return the Membership of user in this server (follow parent for sub-channels)."""
        server = self if self.parent_id is None else self.parent
        try:
            return server.memberships.get(user=user)
        except Membership.DoesNotExist:
            return None

    def get_user_role(self, user):
        m = self.get_membership(user)
        return m.role if m else 'user'

    def is_server_admin(self, user):
        return self.get_user_role(user) == 'admin'

    def is_server_mod(self, user):
        return self.get_user_role(user) in ('admin', 'moderator')


class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages'
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'


class Attachment(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = 'image', 'Obraz'
        AUDIO = 'audio', 'Audio'
        FILE = 'file', 'Plik'

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True
    )
    dm_message = models.ForeignKey(
        'DirectMessage', on_delete=models.CASCADE, related_name='attachments', null=True, blank=True
    )
    file = models.FileField(upload_to='attachments/')
    attachment_type = models.CharField(max_length=10, choices=AttachmentType.choices, default=AttachmentType.FILE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.attachment_type}: {self.file.name}'


class DirectMessage(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_dms'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_dms'
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'DM {self.sender} → {self.recipient}'


class Reaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f'{self.user.username} {self.emoji} on msg {self.message_id}'


class Membership(models.Model):
    """Per-server role assignment and ban status for each user."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        MODERATOR = 'moderator', 'Moderator'
        USER = 'user', 'Użytkownik'

    server = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_banned = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['server', 'user']]
        ordering = ['role', 'user__username']

    def __str__(self):
        return f'{self.user.username} @ {self.server.name} ({self.role})'
