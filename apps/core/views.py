from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    return redirect('chat:channel_list')


def custom_404(request, exception):
    return render(request, 'core/404.html', status=404)


def custom_500(request):
    return render(request, 'core/500.html', status=500)
