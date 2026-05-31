import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.group_name = f'notifications_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('action') == 'mark_read':
            notif_id = data.get('id')
            if notif_id:
                await self.mark_notification_read(notif_id)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event['id'],
            'notif_type': event['notif_type'],
            'title': event['title'],
            'message': event.get('message', ''),
            'url': event.get('url', ''),
        }))

    @database_sync_to_async
    def mark_notification_read(self, notif_id):
        from apps.notifications.models import Notification
        Notification.objects.filter(id=notif_id, recipient=self.scope['user']).update(is_read=True)
