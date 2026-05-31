from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from apps.users.decorators import role_required
from apps.users.models import CustomUser
from apps.chat.models import Message
from .models import BlockedUser, Report


@login_required
@require_POST
def block_user(request, username):
    target = get_object_or_404(CustomUser, username=username)
    if target == request.user:
        return JsonResponse({'error': 'Nie możesz zablokować siebie.'}, status=400)
    BlockedUser.objects.get_or_create(blocker=request.user, blocked=target)
    messages.success(request, f'Użytkownik {target.username} został zablokowany.')
    return redirect(request.META.get('HTTP_REFERER', 'chat:channel_list'))


@login_required
@require_POST
def unblock_user(request, username):
    target = get_object_or_404(CustomUser, username=username)
    BlockedUser.objects.filter(blocker=request.user, blocked=target).delete()
    messages.success(request, f'Odblokowano użytkownika {target.username}.')
    return redirect(request.META.get('HTTP_REFERER', 'chat:channel_list'))


@role_required('admin', 'moderator')
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    message.is_deleted = True
    message.save()
    return JsonResponse({'status': 'deleted', 'message_id': message_id})


@login_required
@require_POST
def report_user(request, username):
    target = get_object_or_404(CustomUser, username=username)
    reason = request.POST.get('reason', 'other')
    description = request.POST.get('description', '')
    Report.objects.create(reporter=request.user, reported_user=target, reason=reason, description=description)
    messages.success(request, 'Zgłoszenie zostało przesłane.')
    return redirect(request.META.get('HTTP_REFERER', 'chat:channel_list'))


@role_required('admin', 'moderator')
def moderation_dashboard(request):
    open_reports = Report.objects.filter(is_resolved=False).select_related('reporter', 'reported_user')
    blocked_list = BlockedUser.objects.all().select_related('blocker', 'blocked')
    return render(request, 'moderation/dashboard.html', {
        'open_reports': open_reports,
        'blocked_list': blocked_list,
    })


@role_required('admin', 'moderator')
@require_POST
def resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.is_resolved = True
    report.save()
    return redirect('moderation:dashboard')
