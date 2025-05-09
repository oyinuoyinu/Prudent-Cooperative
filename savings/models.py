from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, InvalidOperation, ROUND_DOWN
User = get_user_model()


class SavingsPlanType(models.Model):
    """Model to manage different types of savings plans"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0)]
    )
    minimum_duration_months = models.PositiveIntegerField(default=24)  # 2 years default
    minimum_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ['name']



class PaymentAccount(models.Model):

    # PLAN_CHOICES = [
    #     ('Regular', 'Regular Savings'),
    #     ('Investment', 'Investment Savings'),
    #     ('Children', 'Children Savings'),
    # ]

    # PLAN_CHOICES = [
    #     ('Ordinary', 'Ordinary Savings'),
    #     ('Special', 'Special Savings'),
    # ]

    # plan_type = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    plan_type = models.ForeignKey(SavingsPlanType, on_delete=models.PROTECT, related_name="payment_accounts", null=True, blank=True)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=255)

    def __str__(self):
        plan_name = self.plan_type.display_name if self.plan_type else "No Plan"
        return f"{self.bank_name} - {self.account_number} ({plan_name})"


class SavingsPlan(models.Model):
    # PLAN_CHOICES = [
    #     ('Regular', 'Regular Savings'),
    #     ('Investment', 'Investment Savings'),
    #     ('Children', 'Children Savings'),
    # ]
    # PLAN_CHOICES = [
    #     ('Ordinary', 'Ordinary Savings'),
    #     ('Special', 'Special Savings'),
    # ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('matured', 'Matured'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan_type = models.ForeignKey(SavingsPlanType, on_delete=models.PROTECT, related_name="savings_plans", null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    payment_account = models.ForeignKey(PaymentAccount, on_delete=models.PROTECT, related_name="savings_plans")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    maturity_date = models.DateField(null=True, blank=True)
    last_transaction_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.payment_account:
            self.payment_account = PaymentAccount.objects.get(plan_type=self.plan_type)

        if not self.maturity_date:
            self.maturity_date = timezone.now().date() + timedelta(days=730)  # 2 years restriction

        if self.interest_rate == 0.00:
            self.interest_rate = 10.00  # 10% interest for investment plans

        super().save(*args, **kwargs)

    def calculate_interest(self):
        """Calculate interest based on plan type."""
        if self.plan_type and self.plan_type.default_interest_rate > 0:
            return self.amount * (Decimal(str(self.plan_type.default_interest_rate)) / Decimal('100'))
        return Decimal('0.00')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.plan_type.display_name}"


class SavingsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    savings_plan = models.ForeignKey(SavingsPlan, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2,)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_date = models.DateTimeField(auto_now_add=True)
    payment_proof = models.FileField(upload_to='savings/proofs/', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transactions')
    approval_date = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)

    # def save(self, *args, **kwargs):
    #     if self.status == 'approved' and not self.approval_date:
    #         self.approval_date = timezone.now()

    #         if self.transaction_type == "withdrawal" and self.amount > self.savings_plan.amount:
    #             raise ValueError("Withdrawal amount exceeds savings balance")

    #         # Update the savings balance
    #         if self.transaction_type == "deposit":
    #             self.savings_plan.amount += self.amount
    #         elif self.transaction_type == "withdrawal":
    #             self.savings_plan.amount -= self.amount

    #         self.savings_plan.last_transaction_date = timezone.now()
    #         self.savings_plan.save()

    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        if self.status == 'approved' and not self.approval_date:
            self.approval_date = timezone.now()

            if self.transaction_type == "withdrawal" and self.amount > self.savings_plan.amount:
                raise ValueError("Withdrawal amount exceeds savings balance")

            # Update the savings balance
            if self.transaction_type == "deposit":
                self.savings_plan.amount = self.savings_plan.amount + Decimal(str(self.amount))
            elif self.transaction_type == "withdrawal":
                self.savings_plan.amount = self.savings_plan.amount - Decimal(str(self.amount))

            self.savings_plan.last_transaction_date = timezone.now()
            self.savings_plan.save()

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} for {self.savings_plan.user.first_name} {self.savings_plan.user.last_name} - {self.savings_plan.plan_type.display_name}"