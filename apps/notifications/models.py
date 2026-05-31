from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotifType(models.TextChoices):
        MESSAGE = 'message', 'Nowa wiadomość'
        DM = 'dm', 'Wiadomość prywatna'
        MENTION = 'mention', 'Wzmianka'
        SYSTEM = 'system', 'Systemowe'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notif_type = models.CharField(max_length=20, choices=NotifType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username}: {self.title}'
