from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError


class MembershipApplication(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    SAVINGS_CHOICES = (
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    )

    BANK_CHOICES = [
        ('ACCESS', 'Access Bank'),
        ('CITIBANK', 'Citibank Nigeria'),
        ('ECOBANK', 'Ecobank Nigeria'),
        ('FIDELITY', 'Fidelity Bank'),
        ('FCMB', 'First City Monument Bank'),
        ('FSDH', 'FSDH Merchant Bank'),
        ('GTB', 'Guaranty Trust Bank'),
        ('HERITAGE', 'Heritage Bank'),
        ('KEYSTONE', 'Keystone Bank'),
        ('POLARIS', 'Polaris Bank'),
        ('PROVIDUS', 'Providus Bank'),
        ('STANBIC', 'Stanbic IBTC Bank'),
        ('STANDARD', 'Standard Chartered Bank'),
        ('STERLING', 'Sterling Bank'),
        ('SUNTRUST', 'SunTrust Bank'),
        ('TITAN', 'Titan Trust Bank'),
        ('UBA', 'United Bank for Africa'),
        ('UNION', 'Union Bank'),
        ('UNITY', 'Unity Bank'),
        ('WEMA', 'Wema Bank'),
        ('ZENITH', 'Zenith Bank'),
    ]

    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    application_number = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    state_of_origin = models.CharField(max_length=50)
    state_of_residence = models.CharField(max_length=50)
    profession = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    profile_picture = models.ImageField(upload_to='member_pictures/', verbose_name="Soft Picture for Induction")

    # Bank Information
    bank_name = models.CharField(max_length=20, choices=BANK_CHOICES, help_text="Select your bank", null=True, blank=True)
    account_name = models.CharField(max_length=100, help_text="Enter your account name as it appears in your bank", null=True, blank=True)
    account_number = models.CharField(max_length=10, help_text="Enter your 10-digit account number", null=True, blank=True)

    # Savings Information
    savings_type = models.CharField(max_length=10, choices=SAVINGS_CHOICES)

    # Next of Kin Information
    next_of_kin_name = models.CharField(max_length=100)
    next_of_kin_relationship = models.CharField(max_length=50)
    next_of_kin_phone = models.CharField(max_length=20)

    # Referral Information
    how_did_you_hear = models.CharField(max_length=200, verbose_name="How did you hear about us?")
    referrer_name = models.CharField(max_length=100, blank=True, null=True)
    referrer_is_member = models.BooleanField(default=False)

    # Payment Information (Combined Payment)
    payment_completed = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    # Status Information
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = f"PWC{timezone.now().strftime('%y%m')}{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application_number} - {self.full_name}"


class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    membership_number = models.CharField(max_length=20, unique=True, editable=False)
    application = models.OneToOneField(MembershipApplication, on_delete=models.SET_NULL, null=True)
    join_date = models.DateField(default=timezone.now)  # Fixed the default
    is_active = models.BooleanField(default=True)
    blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.membership_number:
            year = str(timezone.now().year)[2:]
            with transaction.atomic():
                last_member = Member.objects.select_for_update().order_by('-membership_number').first()
                if last_member and last_member.membership_number[:2] == year:
                    number = int(last_member.membership_number[2:]) + 1
                else:
                    number = 1
                self.membership_number = f"{year}{number:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        if self.blacklisted and not self.blacklist_reason:
            raise ValidationError("Blacklist reason is required when blacklisted is True.")

    def __str__(self):
        return f"{self.membership_number} - {self.user.first_name} {self.user.last_name}"



def is_member(self):
    """
    Check if user is an approved member
    """
    try:
        return (
            hasattr(self, 'member') and
            self.member is not None and
            self.member.is_active and
            not self.member.blacklisted
        )
    except Member.DoesNotExist:
        return False

User.is_member = property(is_member)




class PaymentVerification(models.Model):
    PAYMENT_TYPES = (
        ('REGISTRATION', 'Registration Fee'),
        ('WELFARE', 'Welfare Fee'),
    )

    application = models.ForeignKey(MembershipApplication, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_proof = models.FileField(upload_to='payment_verifications/')
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_payments')
    verification_date = models.DateTimeField(null=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['application', 'payment_type']

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.application.full_name}"
