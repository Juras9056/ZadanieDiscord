from django.urls import path
from . import views

app_name = 'moderation'

urlpatterns = [
    path('dashboard/', views.moderation_dashboard, name='dashboard'),
    path('block/<str:username>/', views.block_user, name='block_user'),
    path('unblock/<str:username>/', views.unblock_user, name='unblock_user'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('report/<str:username>/', views.report_user, name='report_user'),
    path('report/<int:report_id>/resolve/', views.resolve_report, name='resolve_report'),
]
