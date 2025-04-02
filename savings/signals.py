from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SavingsTransaction, SavingsPlan
from django.utils import timezone
from decimal import Decimal
import logging
from django.db import transaction

# Set up logger
logger = logging.getLogger(__name__)

@receiver(post_save, sender=SavingsTransaction)
def update_savings_plan_on_transaction(sender, instance, created, **kwargs):
    """
    When a transaction is approved:
    1. Update the savings plan balance
    2. Update last transaction date
    3. Check for plan maturity
    4. Send notification
    """
    try:
        if instance.status == 'approved':
            with transaction.atomic():
                plan = instance.savings_plan
                old_balance = plan.amount

                # Update plan balance
                if instance.transaction_type == 'deposit':
                    plan.amount += Decimal(str(instance.amount))
                    transaction_desc = "deposited"
                elif instance.transaction_type == 'withdrawal':
                    if plan.amount >= instance.amount:
                        plan.amount -= Decimal(str(instance.amount))
                        transaction_desc = "withdrawn"
                    else:
                        raise ValueError("Insufficient balance for withdrawal")

                # Update last transaction date
                plan.last_transaction_date = timezone.now()

                # Check if investment plan has matured
                if plan.plan_type.is_investment and plan.maturity_date and timezone.now().date() >= plan.maturity_date:
                    plan.status = 'matured'

                    # Send maturity notification
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=plan.user,
                        title="Investment Plan Matured",
                        message=f"Your {plan.plan_type.display_name} investment plan has matured. Current balance: ₦{plan.amount:,.2f}",
                        notification_type='info'
                    )

                plan.save()
                logger.info(f"Updated savings plan balance from ₦{old_balance:,.2f} to ₦{plan.amount:,.2f}")

                # Send transaction notification
                from notifications.models import Notification
                Notification.objects.create(
                    user=plan.user,
                    title="Savings Transaction",
                    message=f"₦{instance.amount:,.2f} has been {transaction_desc} from your {plan.plan_type.display_name} savings plan. New balance: ₦{plan.amount:,.2f}",
                    notification_type='success' if instance.transaction_type == 'deposit' else 'warning'
                )

    except Exception as e:
        logger.error(f"Error processing savings transaction {instance.id}: {str(e)}")
        raise