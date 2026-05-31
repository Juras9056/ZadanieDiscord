from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Discover / server list
    path('', views.channel_list, name='channel_list'),
    # Server (top-level)
    path('server/create/', views.create_channel, name='create_channel'),
    path('server/<int:server_id>/', views.server_detail, name='server_detail'),
    path('server/<int:server_id>/join/', views.join_channel, name='join_channel'),
    path('server/<int:server_id>/sub/create/', views.create_sub_channel, name='create_sub_channel'),
    # Sub-channels
    path('channel/<int:channel_id>/', views.channel_detail, name='channel_detail'),
    path('voice/<int:channel_id>/', views.voice_channel, name='voice_channel'),
    # Members management
    path('server/<int:server_id>/members/', views.manage_members, name='manage_members'),
    path('server/<int:server_id>/members/<int:user_id>/role/', views.set_member_role, name='set_member_role'),
    path('server/<int:server_id>/members/<int:user_id>/ban/', views.ban_member, name='ban_member'),
    # DMs
    path('dm/<str:username>/', views.dm_conversation, name='dm_conversation'),
    path('dm/<str:username>/voice/', views.dm_voice_call, name='dm_voice_call'),
    # Misc
    path('upload/', views.upload_attachment, name='upload_attachment'),
    path('message/<int:message_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    path('search/', views.search, name='search'),
]
