from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.conf import settings

User = get_user_model()

class LoanTenure(models.Model):
    """Model to define different loan tenures and their interest rates"""
    # PLAN_CHOICES = [
    #     ('emergency', 'Emergency Loan'),
    #     ('normal', 'Normal Loan'),
    #     ('long_term', 'Long-term Loan'),
    # ]

    PLAN_CHOICES = [
        ('Personal', 'Personal Loan'),
        ('Empowerment', 'Empowerment Loan'),
    ]

    plan_type = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    months = models.PositiveIntegerField(unique=True)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['months']

    def __str__(self):
        return f"{self.months} months ({self.interest_rate}% interest)"

class LoanPlan(models.Model):
    """Model to define different types of loan plans"""
    # PLAN_TYPES = [
    #     ('emergency', 'Emergency Loan'),
    #     ('normal', 'Normal Loan'),
    #     ('long_term', 'Long-term Loan'),
    # ]

    PLAN_TYPES = [
        ('Personal', 'Personal Loan'),
        ('Empowerment', 'Empowerment Loan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="loan_plans")
    plan_type = models.CharField(max_length=50, choices=PLAN_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    loan_tenure = models.ForeignKey(LoanTenure, on_delete=models.PROTECT, related_name="loan_plans")
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # available_tenures = models.ManyToManyField(LoanTenure)
    requirements = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.plan_type == 'investment' and self.interest_rate == 0.00:
            self.interest_rate = 10.00  # 10% interest for investment plans

        # Ensure that the minimum and maximum amounts are correctly set
        if self.min_amount > self.max_amount:
            raise ValueError(
                "Minimum amount cannot be greater than maximum amount"
            )

        super().save(*args, **kwargs)

    def calculate_interest(self):
        """Calculate interest based on plan type."""
        if self.plan_type == 'investment':
            return self.amount * (self.interest_rate / 100)
        return 0.00

    def __str__(self):
        return f"{self.plan_type} ({self.loan_tenure})"

class Guarantor(models.Model):
    """Model for loan guarantors"""
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    loan_application = models.ForeignKey(
        'LoanApplication',
        on_delete=models.CASCADE,
        related_name='loan_guarantors'
    )
    relationship = models.CharField(max_length=100)
    occupation = models.CharField(max_length=100)
    address = models.TextField()
    id_card = models.FileField(
        upload_to='guarantors/id_cards/',
        null=True,
        blank=True,
        help_text='Upload a valid government-issued ID card (e.g., National ID, Driver\'s License)'
    )
    guarantee_letter = models.FileField(
        upload_to='guarantors/letters/',
        null=True,
        blank=True,
        help_text='Upload a signed guarantee letter'
    )
    has_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.relationship})"

class LoanApplication(models.Model):
    """Model for loan applications"""

    STATUS_CHOICES = [
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_applications')
    loan_plan = models.ForeignKey(LoanPlan, on_delete=models.PROTECT)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Remaining loan balance
    tenure = models.ForeignKey(LoanTenure, on_delete=models.PROTECT)
    purpose = models.TextField()
    guarantors = models.ManyToManyField('Guarantor', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='under_review')
    application_date = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='reviewed_applications')
    review_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    date_approved = models.DateTimeField(blank=True, null=True)
    date_disbursed = models.DateTimeField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)  # Next repayment due date
    # Payment fields
    has_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)  # Default application fee is ₦1500

    def __str__(self):
        return f"Loan Application #{self.id} - {self.user}"

    def get_payment_status_display(self):
        if self.has_paid:
            return "Paid"
        return "Pending Payment"

class Loan(models.Model):
    """Model for managing loans and their lifecycle"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('defaulted', 'Defaulted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('on_schedule', 'On Schedule'),
        ('late', 'Late'),
        ('defaulted', 'Defaulted'),
    ]

    # Core Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    application = models.OneToOneField(LoanApplication, on_delete=models.PROTECT)
    loan_plan = models.ForeignKey(LoanPlan, on_delete=models.PROTECT, related_name="loan_list")

    # Amount Fields
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2)
    total_payable = models.DecimalField(max_digits=12, decimal_places=2)
    loan_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_disbursed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status Fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='on_schedule'
    )
    payment_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of loan amount paid"
    )

    # Date Fields
    disbursement_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    final_payment_date = models.DateField()
    completion_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan #{self.id} - {self.user.first_name} {self.user.last_name}"

    def calculate_next_payment_date(self):
        """Calculate the next payment date based on payment frequency"""
        if not self.next_payment_date:
            return None

        current_date = timezone.now().date()
        if current_date > self.next_payment_date:
            frequency_days = 30 if self.loan_plan.payment_frequency == 'monthly' else 7
            while self.next_payment_date < current_date:
                self.next_payment_date += timezone.timedelta(days=frequency_days)
        return self.next_payment_date

    def get_payment_status(self):
        """Calculate current payment status based on dates and payments"""
        if self.status == 'completed':
            return 'completed'

        if not self.next_payment_date or not self.disbursement_date:
            return 'pending'

        current_date = timezone.now().date()
        if current_date > self.next_payment_date:
            days_late = (current_date - self.next_payment_date).days
            if days_late > 90:  # 3 months late
                return 'defaulted'
            return 'late'
        return 'on_schedule'

    def update_payment_progress(self):
        """Update payment progress percentage"""
        if self.loan_amount and self.total_paid:
            self.payment_progress = (self.total_paid / self.loan_amount) * 100
            self.save(update_fields=['payment_progress'])

    def get_remaining_installments(self):
        """Calculate remaining installments"""
        if self.status == 'completed':
            return 0
        return round(self.loan_balance / self.monthly_payment)

    def is_eligible_for_disbursement(self, amount):
        """Check if loan is eligible for additional disbursement"""
        if self.status != 'active':
            return False
        return (self.total_disbursed + amount) <= self.loan_amount

    def process_payment(self, amount):
        """Process a loan payment and update relevant fields"""
        if amount > self.loan_balance:
            amount = self.loan_balance

        self.loan_balance -= amount
        self.total_paid = (self.total_paid or 0) + amount

        if self.loan_balance <= 0:
            self.status = 'completed'
            self.loan_balance = 0
            self.completion_date = timezone.now()

        self.update_payment_progress()
        self.payment_status = self.get_payment_status()
        self.save()

        return True

    def get_payment_schedule(self):
        """Generate payment schedule for the loan"""
        if not self.disbursement_date:
            return []

        schedule = []
        remaining_balance = self.total_payable
        payment_date = self.disbursement_date
        payment_number = 1

        while remaining_balance > 0:
            # Monthly payments
            payment_date = payment_date + timezone.timedelta(days=30)

            payment = {
                'payment_number': payment_number,
                'due_date': payment_date,
                'amount': min(self.monthly_payment, remaining_balance),
                'remaining_balance': max(0, remaining_balance - self.monthly_payment)
            }
            schedule.append(payment)

            remaining_balance = payment['remaining_balance']
            payment_number += 1

        return schedule

class LoanTransaction(models.Model):
    """Model for loan repayment transactions"""
    TRANSACTION_TYPES = [
        ('disbursement', 'Disbursement'),
        ('repayment', 'Repayment'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('online', 'Online Payment'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='transactions')
    loan_plan = models.ForeignKey(LoanPlan, on_delete=models.PROTECT, related_name='plan_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    payment_proof = models.FileField(upload_to='loan_payments/', null=True, blank=True)
    reference_number = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loan_transactions'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        # Generate reference number if not provided
        if not self.reference_number:
            prefix = 'DIS' if self.transaction_type == 'disbursement' else 'REP'
            self.reference_number = f"{prefix}-{self.loan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)
