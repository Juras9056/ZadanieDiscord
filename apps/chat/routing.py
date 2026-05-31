from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<channel_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/voice/(?P<channel_id>\d+)/$', consumers.VoiceConsumer.as_asgi()),
    re_path(r'ws/dm/(?P<username>[\w.@+-]+)/$', consumers.DMConsumer.as_asgi()),
    re_path(r'ws/voice-dm/(?P<username>[\w.@+-]+)/$', consumers.DMVoiceConsumer.as_asgi()),
]
