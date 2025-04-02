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
        interest_rate = Decimal(str(instance.loan_plan.plan_type.default_interest_rate)) / Decimal('100')
        months_ratio = Decimal(str(instance.loan_plan.plan_type.minimum_duration_months)) / Decimal('12')
        total_interest = Decimal(str(instance.loan_amount)) * interest_rate * months_ratio
        total_payable = Decimal(str(instance.loan_amount)) + total_interest
        monthly_payment = total_payable / Decimal(str(instance.loan_plan.plan_type.minimum_duration_months))

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
                'final_payment_date': timezone.now().date() + timezone.timedelta(days=30 * instance.loan_plan.plan_type.minimum_duration_months)
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
                description=f'Initial loan disbursement for {instance.loan_plan.plan_type.display_name}'
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
    if instance.status == 'approved':
        loan = instance.loan

        if instance.transaction_type == 'disbursement':
            # Update loan disbursement info
            loan.total_disbursed = Decimal(str(instance.amount))
            loan.disbursement_date = instance.payment_date
            loan.next_payment_date = instance.payment_date + timezone.timedelta(days=30)
            loan.status = 'active'

        elif instance.transaction_type == 'repayment':
            # Update loan balance
            loan.loan_balance -= instance.amount

            # Update next payment date
            if loan.loan_balance > 0:
                loan.next_payment_date = instance.payment_date + timezone.timedelta(days=30)

            # Check if loan is fully repaid
            if loan.loan_balance <= 0:
                loan.status = 'completed'
                loan.payment_status = 'paid'
            else:
                # Update payment status based on schedule
                if instance.payment_date <= loan.next_payment_date:
                    loan.payment_status = 'up_to_date'
                else:
                    loan.payment_status = 'late'

        loan.save()

        # Update loan plan total amount
        total_disbursed = (
            LoanTransaction.objects
            .filter(loan_plan=instance.loan_plan, transaction_type='disbursement', status='approved')
            .aggregate(total=Sum('amount'))
        )
        instance.loan_plan.amount = total_disbursed['total'] or Decimal('0')