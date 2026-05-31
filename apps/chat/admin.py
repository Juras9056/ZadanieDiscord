from django.contrib import admin
from .models import Channel, Message, Attachment, DirectMessage, Reaction


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel_type', 'created_by', 'created_at')
    filter_horizontal = ('members',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('author', 'channel', 'content', 'created_at', 'is_deleted')
    list_filter = ('channel', 'is_deleted')


admin.site.register(Attachment)
admin.site.register(DirectMessage)
admin.site.register(Reaction)
