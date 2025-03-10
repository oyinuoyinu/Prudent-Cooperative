from django.contrib import admin
from .models import Loan, LoanApplication, LoanTransaction, LoanPlan, LoanTenure, Guarantor

# Register your models here.

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('user', 'loan_amount', 'monthly_payment', 'disbursement_date', 'status')
    list_filter = ('status', 'disbursement_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    fieldsets = (
        (None, {
            'fields': ('user', 'application', 'loan_plan', 'loan_amount', 'monthly_payment', 'total_payable', 'loan_balance', 'status')
        }),
        ('Payment Information', {
            'fields': ('total_paid', 'payment_status', 'payment_progress'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('disbursement_date', 'next_payment_date', 'final_payment_date', 'completion_date'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('payment_progress', 'total_paid', 'completion_date')

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'loan_amount', 'status', 'application_date', 'application_fee', 'loan_plan', 'tenure', 'purpose', 'has_paid')
    list_filter = ('status', 'application_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    readonly_fields = ('application_date',)
    fieldsets = (
        (None, {
            'fields': ('user', 'loan_plan', 'loan_amount', 'loan_balance', 'purpose', 'status', 'guarantors')
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'review_date', 'review_notes'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanTenure)
class LoanTenureAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'months', 'interest_rate',)
    list_filter = ('plan_type', )
    search_fields = ('plan_type',)
    fieldsets = (
        (None, {
            'fields': ('plan_type', 'months', 'interest_rate')
        }),

    )

@admin.register(LoanPlan)
class LoanPlanAdmin(admin.ModelAdmin):
    exclude = ('created_at', 'updated_at')
    list_display = ('plan_type', 'loan_tenure', 'min_amount', 'max_amount', )
    list_filter = ('plan_type', )
    search_fields = ('plan_type', 'loan_tenure__plan_type')


@admin.register(LoanTransaction)
class LoanTransactionAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'payment_date', 'status', 'transaction_type')
    list_filter = ('status', 'payment_date')
    search_fields = ('loan__user__first_name', 'loan__user__last_name', 'loan__user__username')
    fieldsets = (
        (None, {
            'fields': ('loan', 'transaction_type', 'amount', 'status', 'payment_method', 'payment_proof', 'reference_number')
        }),
        ('Dates and Approval', {
            'fields': ('approval_date',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'relationship', 'has_verified')
    list_filter = ('has_verified', 'created_at')
    search_fields = ('full_name', 'email', 'phone_number')
    fieldsets = (
        (None, {
            'fields': ('full_name', 'email', 'phone_number', 'relationship', 'occupation', 'address', 'loan_application')
        }),
        ('Documents', {
            'fields': ('id_card', 'guarantee_letter'),
            'description': 'Upload required documents for verification'
        }),
        ('Verification Status', {
            'fields': ('has_verified', 'verification_date'),
            'classes': ('collapse',)
        }),
    )
