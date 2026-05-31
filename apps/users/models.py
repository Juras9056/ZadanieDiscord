from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        MODERATOR = 'moderator', 'Moderator'
        USER = 'user', 'Użytkownik'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_online = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_moderator(self):
        return self.role in (self.Role.ADMIN, self.Role.MODERATOR)


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=300, blank=True)

    def __str__(self):
        return f'Profil: {self.user.username}'

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/img/default_avatar.png'


class FriendRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Oczekujące'
        ACCEPTED = 'accepted', 'Zaakceptowane'
        REJECTED = 'rejected', 'Odrzucone'

    from_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sent_friend_requests'
    )
    to_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='received_friend_requests'
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['from_user', 'to_user']]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.from_user} → {self.to_user} ({self.status})'

    @classmethod
    def are_friends(cls, user_a, user_b):
        return cls.objects.filter(
            status='accepted'
        ).filter(
            models.Q(from_user=user_a, to_user=user_b) |
            models.Q(from_user=user_b, to_user=user_a)
        ).exists()

    @classmethod
    def get_friends(cls, user):
        accepted = cls.objects.filter(status='accepted').filter(
            models.Q(from_user=user) | models.Q(to_user=user)
        ).select_related('from_user__profile', 'to_user__profile')
        friends = []
        for fr in accepted:
            friends.append(fr.to_user if fr.from_user == user else fr.from_user)
        return friends
