from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_online', 'is_staff')
    list_filter = ('role', 'is_online', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Rola i status', {'fields': ('role', 'is_online')}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
