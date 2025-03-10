from django.contrib import admin
from .models import MembershipApplication, Member, PaymentVerification

class PaymentVerificationInline(admin.TabularInline):
    model = PaymentVerification
    extra = 0
    readonly_fields = ['verification_date']
    can_delete = False

@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_number', 'full_name', 'status', 'payment_completed',
                    'application_date','bank_name', 'account_number', 'account_name']
    list_filter = ['status', 'payment_completed', 'application_date']
    search_fields = ['application_number', 'full_name', 'email', 'phone_number']
    readonly_fields = ['application_number', 'application_date', 'payment_reference', 'payment_date']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'application_number', 'user', 'full_name', 'date_of_birth',
                'state_of_origin', 'state_of_residence', 'profession',
                'phone_number', 'email', 'profile_picture'
            )
        }),
        ('Savings Information', {
            'fields': ('savings_type',)
        }),
        ('Next of Kin', {
            'fields': ('next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_phone')
        }),
        ('Referral Information', {
            'fields': ('how_did_you_hear', 'referrer_name', 'referrer_is_member')
        }),
        ('Payment Status', {
            'fields': ('payment_completed', 'payment_reference', 'payment_date')
        }),
        ('Application Status', {
            'fields': ('status', 'application_date', 'approval_date', 'rejection_reason')
        }),
        ('Bank Information', {
            'fields': ('bank_name', 'account_number', 'account_name')
        })
    )

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['membership_number', 'get_full_name', 'is_active', 'join_date']
    list_filter = ['is_active', 'join_date', 'blacklisted']
    search_fields = ['membership_number', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['membership_number', 'join_date']

    def get_full_name(self, obj):
        return obj.user.first_name + ' ' + obj.user.last_name
    get_full_name.short_description = 'Full Name'
