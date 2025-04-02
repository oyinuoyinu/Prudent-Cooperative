from django.contrib import admin
from django.utils import timezone
from .models import *

class SavingsPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_type', 'amount', 'created_at', 'maturity_date')
    list_filter = ('plan_type', 'created_at')
    search_fields = ('user__username', 'plan_type', 'created_at')

class SavingsPlanTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'description', 'minimum_duration_months', 'default_interest_rate', 'is_active')
    list_filter = ('is_active', 'default_interest_rate')
    search_fields = ('name', 'display_name', 'description')

class PaymentAccountAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'account_name', 'account_number', 'bank_name')
    list_filter = ('plan_type', 'bank_name')
    search_fields = ('plan_type', 'bank_name')

@admin.action(description='Approve selected transactions')
def approve_transactions(modeladmin, request, queryset):
    for transaction in queryset:
        if transaction.status == 'pending':
            transaction.status = 'approved'
            transaction.approved_by = request.user
            transaction.approval_date = timezone.now()
            transaction.save()

class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ('savings_plan', 'transaction_type', 'amount', 'status', 'transaction_date', 'approved_by')
    list_filter = ('transaction_type', 'status', 'transaction_date')
    search_fields = ('savings_plan__user__username', 'reference_number')
    readonly_fields = ('reference_number', 'transaction_date', 'approval_date')
    actions = [approve_transactions]

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data and obj.status == 'approved':
            obj.approved_by = request.user
            obj.approval_date = timezone.now()
        super().save_model(request, obj, form, change)

admin.site.register(SavingsPlan, SavingsPlanAdmin)
admin.site.register(SavingsPlanType, SavingsPlanTypeAdmin)
admin.site.register(PaymentAccount, PaymentAccountAdmin)
admin.site.register(SavingsTransaction, SavingsTransactionAdmin)
