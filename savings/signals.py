from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging
from django.db import transaction
from .models import SavingsTransaction

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
    if instance.status != 'approved':
        return

    try:
        with transaction.atomic():
            plan = instance.savings_plan
            old_balance = plan.amount

            # Update plan balance
            if instance.transaction_type == 'deposit':
                plan.amount += instance.amount
            elif instance.transaction_type == 'withdrawal':
                if plan.amount < instance.amount:
                    raise ValueError("Insufficient balance for withdrawal")
                plan.amount -= instance.amount

            # Update last transaction date and check maturity
            plan.last_transaction_date = timezone.now()
            if plan.maturity_date and timezone.now().date() >= plan.maturity_date:
                plan.status = 'matured'

                # Send maturity notification
                Notification.objects.create(
                    user=plan.user,
                    title="Savings Plan Matured",
                    message=(
                        f"Your {plan.plan_type.display_name} plan has matured. "
                        f"Current balance: ₦{plan.amount:,.2f}"
                    ),
                    notification_type='savings'
                )

            plan.save()
            logger.info(
                f"Updated savings plan {plan.id} balance: "
                f"₦{old_balance:,.2f} → ₦{plan.amount:,.2f}"
            )

            # # Send transaction notification
            # action = "deposited into" if instance.transaction_type == 'deposit' else "withdrawn from"
            # Notification.objects.create(
            #     user=plan.user,
            #     title=f"Savings {instance.transaction_type.title()}",
            #     message=(
            #         f"₦{instance.amount:,.2f} has been {action} your "
            #         f"{plan.plan_type.display_name} savings plan. "
            #         f"New balance: ₦{plan.amount:,.2f}"
            #     ),
            #     notification_type='savings'
            # )

    except ValueError as e:
        logger.error(
            f"Validation error processing transaction {instance.id}: {str(e)}"
        )
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error processing transaction {instance.id}: {str(e)}"
        )
        raise