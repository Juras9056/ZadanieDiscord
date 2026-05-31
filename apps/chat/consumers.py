import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'chat_{self.channel_id}'
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_online(user, True)

    async def disconnect(self, close_code):
        user = self.scope['user']
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.set_online(user, False)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')

        if message_type == 'chat_message':
            content = data.get('content', '').strip()
            if not content:
                return
            message = await self.save_message(user, content)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message.id,
                    'content': content,
                    'author': user.username,
                    'avatar': await self.get_avatar(user),
                    'timestamp': message.created_at.strftime('%H:%M'),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'content': event['content'],
            'author': event['author'],
            'avatar': event['avatar'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def save_message(self, user, content):
        from apps.chat.models import Message, Channel
        channel = Channel.objects.get(id=self.channel_id)
        return Message.objects.create(channel=channel, author=user, content=content)

    @database_sync_to_async
    def get_avatar(self, user):
        return user.profile.get_avatar_url()

    @database_sync_to_async
    def set_online(self, user, status):
        from apps.users.models import CustomUser
        CustomUser.objects.filter(pk=user.pk).update(is_online=status)


class DMConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        users = sorted([user.username, self.other_username])
        self.room_group_name = f'dm_{"_".join(users)}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        data = json.loads(text_data)
        content = data.get('content', '').strip()
        if not content:
            return
        dm = await self.save_dm(user, content)
        avatar = await self.get_avatar(user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'dm_message',
                'dm_id': dm.id,
                'content': content,
                'author': user.username,
                'avatar': avatar,
                'timestamp': dm.created_at.strftime('%H:%M'),
            }
        )

    async def dm_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_dm(self, user, content):
        from apps.chat.models import DirectMessage
        from apps.users.models import CustomUser
        recipient = CustomUser.objects.get(username=self.other_username)
        return DirectMessage.objects.create(sender=user, recipient=recipient, content=content)

    @database_sync_to_async
    def get_avatar(self, user):
        return user.profile.get_avatar_url()


class VoiceConsumer(AsyncWebsocketConsumer):
    """WebRTC signaling server for voice channels."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'voice_{self.channel_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        # Notify others that a new peer joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'voice_event', 'event': 'peer_joined', 'username': user.username}
        )

    async def disconnect(self, close_code):
        user = self.scope['user']
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'voice_event', 'event': 'peer_left', 'username': user.username}
        )

    async def receive(self, text_data):
        """Forward WebRTC signaling messages (offer/answer/ice) to the group."""
        user = self.scope['user']
        data = json.loads(text_data)
        data['from'] = user.username
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'voice_signal', 'data': data}
        )

    async def voice_signal(self, event):
        """Send signaling data to this peer (skip self)."""
        data = event['data']
        if data.get('from') != self.scope['user'].username:
            await self.send(text_data=json.dumps(data))

    async def voice_event(self, event):
        await self.send(text_data=json.dumps({
            'type': event['event'],
            'username': event['username'],
        }))


class DMVoiceConsumer(AsyncWebsocketConsumer):
    """WebRTC signaling for private 1-on-1 voice calls via DM."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        # Verify the other user exists and access is valid
        ok = await self.check_access(user.username, self.other_username)
        if not ok:
            await self.close()
            return
        users = sorted([user.username, self.other_username])
        self.room_group_name = f'dm_voice_{"_".join(users)}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'voice_event', 'event': 'peer_joined', 'username': user.username}
        )

    async def disconnect(self, close_code):
        user = self.scope['user']
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'voice_event', 'event': 'peer_left', 'username': user.username}
            )

    async def receive(self, text_data):
        user = self.scope['user']
        data = json.loads(text_data)
        data['from'] = user.username
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'voice_signal', 'data': data}
        )

    async def voice_signal(self, event):
        data = event['data']
        if data.get('from') != self.scope['user'].username:
            await self.send(text_data=json.dumps(data))

    async def voice_event(self, event):
        await self.send(text_data=json.dumps({
            'type': event['event'],
            'username': event['username'],
        }))

    @database_sync_to_async
    def check_access(self, my_username, other_username):
        from apps.users.models import CustomUser
        return CustomUser.objects.filter(username=other_username).exists()



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'chat_{self.channel_id}'
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_online(user, True)

    async def disconnect(self, close_code):
        user = self.scope['user']
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.set_online(user, False)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')

        if message_type == 'chat_message':
            content = data.get('content', '').strip()
            if not content:
                return
            message = await self.save_message(user, content)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message.id,
                    'content': content,
                    'author': user.username,
                    'avatar': await self.get_avatar(user),
                    'timestamp': message.created_at.strftime('%H:%M'),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'content': event['content'],
            'author': event['author'],
            'avatar': event['avatar'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def save_message(self, user, content):
        from apps.chat.models import Message, Channel
        channel = Channel.objects.get(id=self.channel_id)
        return Message.objects.create(channel=channel, author=user, content=content)

    @database_sync_to_async
    def get_avatar(self, user):
        return user.profile.get_avatar_url()

    @database_sync_to_async
    def set_online(self, user, status):
        from apps.users.models import CustomUser
        CustomUser.objects.filter(pk=user.pk).update(is_online=status)


class DMConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        users = sorted([user.username, self.other_username])
        self.room_group_name = f'dm_{"_".join(users)}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        data = json.loads(text_data)
        content = data.get('content', '').strip()
        if not content:
            return
        dm = await self.save_dm(user, content)
        avatar = await self.get_avatar(user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'dm_message',
                'dm_id': dm.id,
                'content': content,
                'author': user.username,
                'avatar': avatar,
                'timestamp': dm.created_at.strftime('%H:%M'),
            }
        )

    async def dm_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_dm(self, user, content):
        from apps.chat.models import DirectMessage
        from apps.users.models import CustomUser
        recipient = CustomUser.objects.get(username=self.other_username)
        return DirectMessage.objects.create(sender=user, recipient=recipient, content=content)

    @database_sync_to_async
    def get_avatar(self, user):
        return user.profile.get_avatar_url()
