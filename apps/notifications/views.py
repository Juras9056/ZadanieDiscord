from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    notifs = request.user.notifications.all()[:50]
    return render(request, 'notifications/list.html', {'notifications': notifs})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications:list')
