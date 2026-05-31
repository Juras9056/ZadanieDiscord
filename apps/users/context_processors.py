from apps.notifications.models import Notification
from apps.chat.models import Channel, Membership
from apps.chat.forms import ChannelForm
from apps.users.models import FriendRequest


def user_context(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        pending_friends = FriendRequest.objects.filter(
            to_user=request.user, status='pending'
        ).count()
        my_servers_qs = (
            Channel.objects.filter(members=request.user, parent__isnull=True)
            .prefetch_related('sub_channels')
            .order_by('name')
        )
        memberships = {
            m.server_id: m
            for m in Membership.objects.filter(user=request.user)
        }
        my_servers = list(my_servers_qs)
        for srv in my_servers:
            mem = memberships.get(srv.id)
            srv.my_role = mem.role if mem else 'user'
            srv.my_is_mod = srv.my_role in ('admin', 'moderator')
        return {
            'my_servers': my_servers,
            'channel_form': ChannelForm(),
            'unread_notifications_count': unread_count,
            'pending_friend_requests': pending_friends,
        }
    return {}


