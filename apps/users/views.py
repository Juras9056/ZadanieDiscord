from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from .forms import RegisterForm, LoginForm, EditProfileForm
from .models import CustomUser, FriendRequest


def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat:channel_list')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Witaj, {user.username}! Konto zostało utworzone.')
        return redirect('chat:channel_list')
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat:channel_list')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(request.GET.get('next', 'chat:channel_list'))
    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('users:login')
    return redirect('chat:channel_list')


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    friend_status = None  # 'friends', 'sent', 'received', None
    pending_req = None
    if request.user != profile_user:
        if FriendRequest.are_friends(request.user, profile_user):
            friend_status = 'friends'
        else:
            sent = FriendRequest.objects.filter(from_user=request.user, to_user=profile_user).first()
            received = FriendRequest.objects.filter(from_user=profile_user, to_user=request.user).first()
            if sent and sent.status == 'pending':
                friend_status = 'sent'
                pending_req = sent
            elif received and received.status == 'pending':
                friend_status = 'received'
                pending_req = received
    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'friend_status': friend_status,
        'pending_req': pending_req,
    })


@login_required
def edit_profile_view(request):
    form = EditProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil zaktualizowany.')
        return redirect('users:profile', username=request.user.username)
    return render(request, 'users/edit_profile.html', {'form': form})


# ─── Friends ────────────────────────────────────────────────────────────────

@login_required
def friends_view(request):
    """List friends, incoming requests, sent requests."""
    friends = FriendRequest.get_friends(request.user)
    incoming = FriendRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user__profile')
    sent = FriendRequest.objects.filter(
        from_user=request.user, status='pending'
    ).select_related('to_user__profile')
    return render(request, 'users/friends.html', {
        'friends': friends,
        'incoming': incoming,
        'sent': sent,
    })


@login_required
@require_POST
def send_friend_request(request, username):
    to_user = get_object_or_404(CustomUser, username=username)
    if to_user == request.user:
        messages.error(request, 'Nie możesz dodać siebie do znajomych.')
        return redirect('users:profile', username=username)
    if FriendRequest.are_friends(request.user, to_user):
        messages.info(request, 'Już jesteście znajomymi.')
        return redirect('users:profile', username=username)
    # Check reverse pending (they already sent to us — auto-accept)
    reverse = FriendRequest.objects.filter(
        from_user=to_user, to_user=request.user, status='pending'
    ).first()
    if reverse:
        reverse.status = 'accepted'
        reverse.save()
        messages.success(request, f'Teraz jesteście znajomymi z {to_user.username}!')
        return redirect('users:profile', username=username)
    _, created = FriendRequest.objects.get_or_create(
        from_user=request.user, to_user=to_user,
        defaults={'status': 'pending'}
    )
    if created:
        messages.success(request, f'Zaproszenie do znajomych wysłane do {to_user.username}.')
    else:
        messages.info(request, 'Zaproszenie zostało już wysłane.')
    return redirect('users:profile', username=username)


@login_required
@require_POST
def respond_friend_request(request, req_id):
    fr = get_object_or_404(FriendRequest, id=req_id, to_user=request.user, status='pending')
    action = request.POST.get('action')
    if action == 'accept':
        fr.status = 'accepted'
        fr.save()
        messages.success(request, f'Zaakceptowałeś zaproszenie od {fr.from_user.username}.')
    elif action == 'reject':
        fr.status = 'rejected'
        fr.save()
        messages.info(request, f'Odrzuciłeś zaproszenie od {fr.from_user.username}.')
    return redirect('users:friends')


@login_required
@require_POST
def remove_friend(request, username):
    other = get_object_or_404(CustomUser, username=username)
    FriendRequest.objects.filter(status='accepted').filter(
        Q(from_user=request.user, to_user=other) |
        Q(from_user=other, to_user=request.user)
    ).delete()
    messages.info(request, f'Usunięto {other.username} ze znajomych.')
    return redirect('users:profile', username=username)
