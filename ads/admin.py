from django.contrib import admin
from .models import Ad, ExchangeProposal, Notification


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'condition', 'is_active', 'created_at')
    list_filter = ('category', 'condition', 'is_active')
    search_fields = ('title', 'description')


@admin.register(ExchangeProposal)
class ExchangeProposalAdmin(admin.ModelAdmin):
    list_display = ('sender', 'ad_sender', 'ad_receiver', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('comment',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('message',)

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Сообщение'