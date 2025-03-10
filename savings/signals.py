from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SavingsTransaction, SavingsPlan
from django.utils import timezone

@receiver(post_save, sender=SavingsTransaction)
def update_savings_plan_on_transaction(sender, instance, created, **kwargs):
    """
    When a transaction is approved, update the savings plan balance
    """
    if instance.status == 'approved':
        plan = instance.savings_plan

        # Update plan balance
        if instance.transaction_type == 'deposit':
            plan.amount += instance.amount
        elif instance.transaction_type == 'withdrawal':
            plan.amount -= instance.amount

        # Update last transaction date
        plan.last_transaction_date = timezone.now()

        # Check if investment plan has matured
        if plan.maturity_date and timezone.now().date() >= plan.maturity_date:
            plan.status = 'matured'

        plan.save()