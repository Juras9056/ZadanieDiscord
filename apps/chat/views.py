from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
import mimetypes
import os
from .models import Channel, Message, DirectMessage, Attachment, Membership
from .forms import ChannelForm, SubChannelForm, JoinPrivateChannelForm, AttachmentUploadForm
from apps.users.models import CustomUser
from apps.users.decorators import role_required


# ─── Server (top-level channel) views ──────────────────────────────────────

@login_required
def channel_list(request):
    """Discover all servers the user hasn't joined yet."""
    joined_ids = request.user.channels.values_list('id', flat=True)
    all_servers = (
        Channel.objects.filter(parent__isnull=True)
        .exclude(id__in=joined_ids)
        .order_by('channel_type', 'name')  # public first
    )
    form = ChannelForm()
    return render(request, 'chat/channel_list.html', {
        'all_servers': all_servers,
        'form': form,
    })


@login_required
def server_detail(request, server_id):
    """Server overview: redirect to first text sub-channel or show sub-channel list."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    _check_server_access(request, server)
    first_text = server.sub_channels.filter(sub_type='text').order_by('name').first()
    if first_text:
        return redirect('chat:channel_detail', channel_id=first_text.id)
    sub_form = SubChannelForm()
    return render(request, 'chat/server_detail.html', {
        'server': server,
        'sub_form': sub_form,
        'active_server': server,
    })


@login_required
@require_POST
def create_channel(request):
    """Create a new top-level server."""
    form = ChannelForm(request.POST)
    if form.is_valid():
        channel = form.save(commit=False)
        channel.parent = None
        channel.sub_type = None
        raw_pw = form.cleaned_data.get('password_raw', '')
        if raw_pw:
            channel.set_password(raw_pw)
        channel.created_by = request.user
        channel.save()
        channel.members.add(request.user)
        Membership.objects.create(server=channel, user=request.user, role='admin')
        return redirect('chat:server_detail', server_id=channel.id)
    return redirect('chat:channel_list')


@login_required
def join_channel(request, server_id):
    """Join a server. Private ones require password confirmation."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    if request.user in server.members.all():
        return redirect('chat:server_detail', server_id=server.id)

    if server.channel_type == 'public':
        server.members.add(request.user)
        Membership.objects.get_or_create(server=server, user=request.user, defaults={'role': 'user'})
        return redirect('chat:server_detail', server_id=server.id)

    # Private — show password form
    if request.method == 'POST':
        form = JoinPrivateChannelForm(request.POST)
        if form.is_valid():
            if server.check_password(form.cleaned_data['password']):
                server.members.add(request.user)
                Membership.objects.get_or_create(server=server, user=request.user, defaults={'role': 'user'})
                messages.success(request, f'Dołączyłeś do serwera #{server.name}.')
                return redirect('chat:server_detail', server_id=server.id)
            else:
                form.add_error('password', 'Nieprawidłowe hasło.')
    else:
        form = JoinPrivateChannelForm()
    return render(request, 'chat/join_private.html', {'server': server, 'form': form})


# ─── Sub-channel views ──────────────────────────────────────────────────────

@login_required
@require_POST
def create_sub_channel(request, server_id):
    """Create a text or voice sub-channel inside a server."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    if not server.is_server_admin(request.user) and not request.user.is_staff:
        messages.error(request, 'Tylko administrator serwera może tworzyć podkanały.')
        return redirect('chat:server_detail', server_id=server.id)
    form = SubChannelForm(request.POST)
    if form.is_valid():
        sub = form.save(commit=False)
        sub.parent = server
        sub.channel_type = server.channel_type
        sub.created_by = request.user
        sub.save()
        if sub.sub_type == 'voice':
            return redirect('chat:voice_channel', channel_id=sub.id)
        return redirect('chat:channel_detail', channel_id=sub.id)
    return redirect('chat:server_detail', server_id=server.id)


@login_required
def channel_detail(request, channel_id):
    """Text sub-channel: show messages and chat input."""
    sub = get_object_or_404(Channel, id=channel_id)
    # Block voice sub-channels — redirect to voice view
    if sub.sub_type == 'voice':
        return redirect('chat:voice_channel', channel_id=sub.id)
    server = sub.parent
    if server:
        _check_server_access(request, server)
    elif sub.channel_type == 'private' and request.user not in sub.members.all():
        messages.error(request, 'Nie masz dostępu do tego kanału.')
        return redirect('chat:channel_list')

    channel_messages = sub.messages.filter(is_deleted=False).select_related(
        'author', 'author__profile'
    ).prefetch_related('attachments', 'reactions').order_by('created_at')

    my_mem = Membership.objects.filter(server=server, user=request.user).first() if server else None
    sub_form = SubChannelForm()
    return render(request, 'chat/channel_detail.html', {
        'channel': sub,
        'server': server,
        'messages_list': channel_messages,
        'active_channel': sub,
        'active_server': server,
        'sub_form': sub_form,
        'my_role': my_mem.role if my_mem else 'user',
        'is_server_mod': my_mem.role in ('admin', 'moderator') if my_mem else False,
        'is_server_admin': my_mem.role == 'admin' if my_mem else False,
    })


@login_required
def voice_channel(request, channel_id):
    """Voice sub-channel: WebRTC signaling page."""
    sub = get_object_or_404(Channel, id=channel_id)
    if sub.sub_type != 'voice':
        return redirect('chat:channel_detail', channel_id=sub.id)
    server = sub.parent
    if server:
        _check_server_access(request, server)
    sub_form = SubChannelForm()
    return render(request, 'chat/voice_channel.html', {
        'channel': sub,
        'server': server,
        'active_channel': sub,
        'active_server': server,
        'sub_form': sub_form,
    })


# ─── Direct Messages ────────────────────────────────────────────────────────

@login_required
def dm_conversation(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    if other_user == request.user:
        return redirect('chat:channel_list')
    conversation = DirectMessage.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).filter(is_deleted=False).select_related('sender', 'sender__profile').prefetch_related('attachments')
    conversation.filter(recipient=request.user, is_read=False).update(is_read=True)
    return render(request, 'chat/dm_conversation.html', {
        'other_user': other_user,
        'conversation': conversation,
    })


@login_required
def dm_voice_call(request, username):
    """Private 1-on-1 voice call page."""
    other_user = get_object_or_404(CustomUser, username=username)
    if other_user == request.user:
        return redirect('chat:channel_list')
    return render(request, 'chat/dm_voice.html', {
        'other_user': other_user,
    })


# ─── Attachments & Reactions ────────────────────────────────────────────────

@login_required
@require_POST
def upload_attachment(request, message_id=None):
    form = AttachmentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': 'Nieprawidłowy plik.'}, status=400)
    file = request.FILES['file']
    mime, _ = mimetypes.guess_type(file.name)
    if mime and mime.startswith('image'):
        att_type = 'image'
    elif mime and mime.startswith('audio'):
        att_type = 'audio'
    else:
        att_type = 'file'
    attachment = Attachment(file=file, attachment_type=att_type)
    if message_id:
        message = get_object_or_404(Message, id=message_id, author=request.user)
        attachment.message = message
    attachment.save()
    return JsonResponse({'url': attachment.file.url, 'type': att_type, 'id': attachment.id})


@login_required
@require_POST
def toggle_reaction(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    emoji = request.POST.get('emoji', '')
    if not emoji:
        return JsonResponse({'error': 'Brak emoji.'}, status=400)
    from .models import Reaction
    reaction, created = Reaction.objects.get_or_create(message=message, user=request.user, emoji=emoji)
    if not created:
        reaction.delete()
        action = 'removed'
    else:
        action = 'added'
    count = message.reactions.filter(emoji=emoji).count()
    return JsonResponse({'action': action, 'emoji': emoji, 'count': count})


@login_required
def search(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        results = Message.objects.filter(
            content__icontains=q, is_deleted=False
        ).select_related('author', 'channel').order_by('-created_at')[:30]
    return render(request, 'chat/search_results.html', {'q': q, 'results': results})


# ─── Roles & Members management ─────────────────────────────────────────────

@login_required
def manage_members(request, server_id):
    """Admin/mod: view all server members, change roles, ban users."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    _check_server_access(request, server)
    my_mem = Membership.objects.filter(server=server, user=request.user).first()
    if not my_mem or my_mem.role not in ('admin', 'moderator'):
        messages.error(request, 'Tylko administrator lub moderator może zarządzać członkami.')
        return redirect('chat:server_detail', server_id=server.id)
    memberships = server.memberships.select_related('user', 'user__profile').order_by('role', 'user__username')
    return render(request, 'chat/members.html', {
        'server': server,
        'memberships': memberships,
        'my_mem': my_mem,
        'active_server': server,
        'role_choices': Membership.Role.choices,
    })


@login_required
@require_POST
def set_member_role(request, server_id, user_id):
    """Admin only: change another member's role."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    my_mem = get_object_or_404(Membership, server=server, user=request.user)
    target_mem = get_object_or_404(Membership, server=server, user_id=user_id)
    if my_mem.role != 'admin':
        messages.error(request, 'Tylko administrator może zmieniać role.')
        return redirect('chat:manage_members', server_id=server.id)
    if target_mem.user == request.user:
        messages.error(request, 'Nie możesz zmienić swojej własnej roli.')
        return redirect('chat:manage_members', server_id=server.id)
    new_role = request.POST.get('role', 'user')
    if new_role not in ('admin', 'moderator', 'user'):
        new_role = 'user'
    target_mem.role = new_role
    target_mem.save()
    messages.success(request, f'Rola użytkownika {target_mem.user.username} zmieniona na {new_role}.')
    return redirect('chat:manage_members', server_id=server.id)


@login_required
@require_POST
def ban_member(request, server_id, user_id):
    """Admin/mod: ban or unban a member."""
    server = get_object_or_404(Channel, id=server_id, parent__isnull=True)
    my_mem = get_object_or_404(Membership, server=server, user=request.user)
    target_mem = get_object_or_404(Membership, server=server, user_id=user_id)
    if my_mem.role not in ('admin', 'moderator'):
        messages.error(request, 'Nie masz uprawnień do banowania.')
        return redirect('chat:manage_members', server_id=server.id)
    if target_mem.role == 'admin':
        messages.error(request, 'Nie można zbanować administratora.')
        return redirect('chat:manage_members', server_id=server.id)
    if my_mem.role == 'moderator' and target_mem.role == 'moderator':
        messages.error(request, 'Moderatorzy nie mogą banować innych moderatorów.')
        return redirect('chat:manage_members', server_id=server.id)
    if target_mem.user == request.user:
        messages.error(request, 'Nie możesz zbanować samego siebie.')
        return redirect('chat:manage_members', server_id=server.id)
    target_mem.is_banned = not target_mem.is_banned
    target_mem.save()
    if target_mem.is_banned:
        server.members.remove(target_mem.user)
        action = 'zbanowany'
    else:
        server.members.add(target_mem.user)
        action = 'odbanowany'
    messages.success(request, f'Użytkownik {target_mem.user.username} został {action}.')
    return redirect('chat:manage_members', server_id=server.id)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _check_server_access(request, server):
    """Redirect if server is private and user has no access (raises redirect)."""
    if server is None:
        return
    if server.channel_type == 'private' and request.user not in server.members.all():
        messages.error(request, 'Nie masz dostępu do tego serwera.')
        from django.http import Http404
        raise Http404
    # Check if banned
    try:
        mem = server.memberships.get(user=request.user)
        if mem.is_banned:
            messages.error(request, 'Zostałeś zbanowany na tym serwerze.')
            from django.http import Http404
            raise Http404
    except Membership.DoesNotExist:
        pass


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    users = []
    channels = []
    if query:
        users = CustomUser.objects.filter(username__icontains=query).exclude(id=request.user.id)[:10]
        channels = Channel.objects.filter(name__icontains=query, channel_type='public')[:10]
    return render(request, 'chat/search_results.html', {
        'query': query,
        'users': users,
        'channels': channels,
    })
