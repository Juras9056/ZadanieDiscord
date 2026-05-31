from django.contrib import admin
from .models import BlockedUser, Report

admin.site.register(BlockedUser)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'is_resolved', 'created_at')
    list_filter = ('reason', 'is_resolved')
