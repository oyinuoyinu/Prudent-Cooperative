from django.contrib import admin
from .models import Loan, LoanApplication, LoanTransaction, LoanPlan, Guarantor, LoanPlanType

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
    list_display = ('user', 'loan_amount', 'status', 'application_date', 'plan_type', 'purpose')
    list_filter = ('status', 'application_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    readonly_fields = ('application_date',)
    fieldsets = (
        (None, {
            'fields': ('user', 'plan_type', 'loan_amount', 'purpose', 'status')
        }),
        ('Review Information', {
            'fields': ('review_notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanPlanType)
class LoanPlanTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'description', 'minimum_duration_months', 'min_amount', 'max_amount', 'default_interest_rate', 'processing_fee_percentage', 'requirements', 'min_credit_score', 'min_membership_duration', 'guarantors_required', 'is_active')
    list_filter = ('is_active', 'min_amount', 'max_amount')
    search_fields = ('name', 'display_name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'description', 'minimum_duration_months', 'min_amount', 'max_amount', 'default_interest_rate', 'processing_fee_percentage', 'requirements', 'min_credit_score', 'min_membership_duration', 'guarantors_required', 'is_active')
        }),

    )

@admin.register(LoanPlan)
class LoanPlanAdmin(admin.ModelAdmin):
    exclude = ('created_at', 'updated_at')
    list_display = ('user', 'plan_type', 'amount', 'min_amount', 'max_amount')
    list_filter = ('plan_type', 'created_at')
    search_fields = ('user__username', 'plan_type__name')

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
