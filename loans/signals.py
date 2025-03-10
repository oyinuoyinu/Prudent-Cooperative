from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum
from .models import LoanTransaction, Loan, LoanApplication
from decimal import Decimal

@receiver(post_save, sender=LoanApplication)
def create_loan_on_disbursement(sender, instance, created, **kwargs):
    """
    When a loan application status changes to 'disbursed':
    1. Create a new Loan instance
    2. Create a LoanTransaction for disbursement
    """
    if instance.status == 'disbursed':
        # Calculate monthly payment and total payable
        interest_rate = Decimal(str(instance.tenure.interest_rate)) / Decimal('100')
        months_ratio = Decimal(str(instance.tenure.months)) / Decimal('12')
        total_interest = Decimal(str(instance.loan_amount)) * interest_rate * months_ratio
        total_payable = Decimal(str(instance.loan_amount)) + total_interest
        monthly_payment = total_payable / Decimal(str(instance.tenure.months))

        # Create Loan instance if it doesn't exist
        loan, created = Loan.objects.get_or_create(
            user=instance.user,
            loan_plan=instance.loan_plan,
            application=instance,
            defaults={
                'status': 'active',
                'loan_amount': Decimal(str(instance.loan_amount)),
                'monthly_payment': monthly_payment,
                'total_payable': total_payable,
                'loan_balance': total_payable,  # Initial balance includes interest
                'total_disbursed': Decimal('0'),  # Will be updated by transaction signal
                'disbursement_date': None,  # Will be set by transaction signal
                'final_payment_date': timezone.now().date() + timezone.timedelta(days=30 * instance.tenure.months)
            }
        )

        if created:
            # Create disbursement transaction
            LoanTransaction.objects.create(
                loan=loan,
                loan_plan=instance.loan_plan,
                amount=Decimal(str(instance.loan_amount)),
                transaction_type='disbursement',
                status='approved',
                payment_date=timezone.now(),
                description=f'Initial loan disbursement for {instance.loan_plan.get_plan_type_display()}'
            )


@receiver(post_save, sender=LoanTransaction)
def update_loan_on_transaction(sender, instance, created, **kwargs):
    """
    Handle all loan transaction scenarios:
    1. Update loan balance and status
    2. Track disbursements and repayments
    3. Update loan plan total amount
    4. Validate transaction amounts
    """
    loan = instance.loan
    loan_plan = instance.loan_plan or loan.loan_plan  # Fallback to loan's plan if not set

    if instance.status == 'approved':
        if instance.transaction_type == 'disbursement':
            # Validate total disbursement against loan amount
            total_disbursed = (loan.total_disbursed or Decimal('0')) + Decimal(str(instance.amount))
            if total_disbursed > Decimal(str(loan.loan_amount)):
                instance.status = 'rejected'
                instance.save()
                return

            # Update total disbursed only, loan_balance is already set correctly in create_loan_on_disbursement
            loan.total_disbursed = total_disbursed

            # Update loan plan total amount
            loan_plan.amount = (loan_plan.amount or Decimal('0')) + Decimal(str(instance.amount))
            loan_plan.save()

            # Set initial disbursement date if not set
            if not loan.disbursement_date:
                loan.disbursement_date = timezone.now()

            # Update loan status
            loan.status = 'active'

            # Update next payment date (monthly schedule)
            loan.next_payment_date = timezone.now().date() + timezone.timedelta(days=30)

        elif instance.transaction_type == 'repayment':
            # Validate payment amount
            if Decimal(str(instance.amount)) > Decimal(str(loan.loan_balance)):
                instance.amount = loan.loan_balance
                instance.save()

            # Update loan balance and payment tracking
            loan.loan_balance -= Decimal(str(instance.amount))
            loan.total_paid = (loan.total_paid or Decimal('0')) + Decimal(str(instance.amount))

            # Update loan plan total amount
            loan_plan.amount = (loan_plan.amount or Decimal('0')) - Decimal(str(instance.amount))
            loan_plan.save()

            # Update payment status
            if loan.next_payment_date and timezone.now().date() <= loan.next_payment_date:
                loan.payment_status = 'on_schedule'
            else:
                loan.payment_status = 'late'

            # Check if loan is fully paid
            if Decimal(str(loan.loan_balance)) <= 0:
                loan.status = 'completed'
                loan.loan_balance = Decimal('0')
                loan.completion_date = timezone.now()
            else:
                # Update next payment date (monthly schedule)
                loan.next_payment_date = timezone.now().date() + timezone.timedelta(days=30)

    elif instance.status == 'rejected':
        if instance.transaction_type == 'disbursement':
            # If it's the initial disbursement and it's rejected, cancel the loan
            if not loan.disbursement_date:
                loan.status = 'cancelled'

    # Calculate payment progress
    if Decimal(str(loan.loan_amount)) and Decimal(str(loan.total_paid)):
        loan.payment_progress = (Decimal(str(loan.total_paid)) / Decimal(str(loan.loan_amount))) * 100

    loan.save()