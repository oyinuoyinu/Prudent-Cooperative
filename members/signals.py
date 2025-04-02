from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
import logging

from .models import MembershipApplication, Member, PaymentVerification
from loans.models import LoanPlan, LoanPlanType
from savings.models import SavingsPlan, PaymentAccount, SavingsPlanType

# Set up logger
logger = logging.getLogger(__name__)

@receiver(post_save, sender=PaymentVerification)
def update_application_payment_status(sender, instance, created, **kwargs):
    """
    When a payment is verified, update the corresponding payment status in the application
    """
    try:
        with transaction.atomic():
            application = instance.application

            # Update payment status based on payment type
            if instance.payment_type == 'REGISTRATION' and instance.verified:
                application.registration_fee_paid = True
                logger.info(f"Registration fee marked as paid for application {application.application_number}")

            elif instance.payment_type == 'WELFARE' and instance.verified:
                application.welfare_fee_paid = True
                logger.info(f"Welfare fee marked as paid for application {application.application_number}")

            # Check if all required payments are completed
            if application.registration_fee_paid and application.welfare_fee_paid:
                application.payment_completed = True
                logger.info(f"All payments completed for application {application.application_number}")

            application.save()

    except Exception as e:
        logger.error(f"Error updating payment status for application {instance.application.application_number}: {str(e)}")
        raise

@receiver(post_save, sender=MembershipApplication)
def handle_application_approval(sender, instance, created, **kwargs):
    """
    When an application is approved and all payments are verified, create member profile
    """
    try:
        with transaction.atomic():
            # Only proceed if application is approved and all payments are verified
            if instance.status == 'APPROVED' and instance.payment_completed:
                # Create or update member profile
                member, created = Member.objects.get_or_create(
                    user=instance.user,
                    defaults={
                        'application': instance,
                        'join_date': timezone.now().date(),
                    }
                )

                if created:
                    logger.info(f"Created new member profile {member.membership_number} for application {instance.application_number}")
                else:
                    # Update existing member if needed
                    if member.application != instance:
                        member.application = instance
                        member.save()
                        logger.info(f"Updated member profile {member.membership_number} with new application {instance.application_number}")

                # Set approval date if not set
                if not instance.approval_date:
                    instance.approval_date = timezone.now()
                    instance.save()
                    logger.info(f"Set approval date for application {instance.application_number}")

            elif instance.status == 'REJECTED' and not instance.rejection_reason:
                logger.warning(f"Application {instance.application_number} was rejected without a reason")

    except Exception as e:
        logger.error(f"Error handling application {instance.application_number} approval: {str(e)}")
        raise

@receiver(post_save, sender=Member)
def handle_member_creation(sender, instance, created, **kwargs):
    """
    When a new member is created, create loan and savings plans
    """
    logger.info(f"Member creation signal triggered for {instance.membership_number}")

    try:
        with transaction.atomic():
            # Only create plans if this is a new member
            if created:
                # Create loan plans for each active loan type
                for loan_type in LoanPlanType.objects.filter(is_active=True):
                    try:
                        # Check if plan already exists
                        if not LoanPlan.objects.filter(user=instance.user, plan_type=loan_type).exists():
                            logger.info(f"Creating {loan_type.display_name} loan plan for user {instance.user.username}")

                            LoanPlan.objects.create(
                                user=instance.user,
                                plan_type=loan_type,
                                amount=0,
                                status='active'
                            )
                    except Exception as e:
                        logger.error(f"Error creating loan plan for user {instance.user.username}: {str(e)}")
                        raise

                # Create savings plans for each active savings type
                for savings_type in SavingsPlanType.objects.filter(is_active=True):
                    try:
                        # Check if plan already exists
                        if not SavingsPlan.objects.filter(user=instance.user, plan_type=savings_type).exists():
                            logger.info(f"Creating {savings_type.display_name} savings plan for user {instance.user.username}")

                            # Create the savings plan
                            savings_plan = SavingsPlan.objects.create(
                                user=instance.user,
                                plan_type=savings_type,
                                amount=0,
                                status='active',
                                start_date=timezone.now().date()
                            )

                            # Create a payment account for this plan type if it doesn't exist
                            if not PaymentAccount.objects.filter(plan_type=savings_type).exists():
                                PaymentAccount.objects.create(
                                    plan_type=savings_type,
                                    account_name=f"{savings_type.display_name} Account",
                                    account_number="TBD",  # This should be updated by admin
                                    bank_name="TBD"  # This should be updated by admin
                                )
                    except Exception as e:
                        logger.error(f"Error creating savings plan for user {instance.user.username}: {str(e)}")
                        raise

    except Exception as e:
        logger.error(f"Error in member creation signal for {instance.membership_number}: {str(e)}")
        raise
