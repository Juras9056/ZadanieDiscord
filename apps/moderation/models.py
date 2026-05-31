from django.db import models
from django.conf import settings


class BlockedUser(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocking'
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f'{self.blocker} blokuje {self.blocked}'


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = 'spam', 'Spam'
        HARASSMENT = 'harassment', 'Nękanie'
        INAPPROPRIATE = 'inappropriate', 'Nieodpowiednie treści'
        OTHER = 'other', 'Inne'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made'
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received',
        null=True, blank=True
    )
    reported_message = models.ForeignKey(
        'chat.Message', on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f'Zgłoszenie od {self.reporter} — {self.reason}'
