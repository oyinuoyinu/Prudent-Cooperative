# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # from accounts.models import User, UserProfile
# # from .models import Member

# # @receiver(post_save, sender=User)
# # def create_profile_for_member(sender, instance, created, **kwargs):
# #     if created and instance.role == User.MEMBER:
# #         UserProfile.objects.create(user=instance)
# #         member = Member.objects.create(
# #             user=instance,
# #             user_profile=UserProfile.objects.get(user=instance),
# #             member_slug=f"{instance.username}-{instance.id}"
# #         )






# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import MembershipApplication, Member, PaymentVerification
# from django.utils import timezone

# @receiver(post_save, sender=PaymentVerification)
# def update_application_on_payment_verification(sender, instance, created, **kwargs):
#     """
#     When payment is verified, update application status
#     """
#     if instance.status == 'verified':
#         application = instance.application
#         application.payment_verified = True
#         application.save()

# @receiver(post_save, sender=MembershipApplication)
# def create_member_on_approval(sender, instance, created, **kwargs):
#     """
#     When application is approved and payment is verified, create member profile
#     """
#     if instance.status == 'approved' and instance.payment_verified:
#         # Create member profile if it doesn't exist
#         Member.objects.get_or_create(
#             user=instance.user,
#             defaults={
#                 'membership_number': instance.generate_membership_number(),
#                 'application': instance
#             }
#         )





from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import MembershipApplication, Member, PaymentVerification
from savings.models import SavingsPlan
from loans.models import LoanPlan
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PaymentVerification)
def update_application_payment_status(sender, instance, created, **kwargs):
    """
    When a payment is verified, update the corresponding payment status in the application
    """
    try:
        with transaction.atomic():
            application = instance.application

            if instance.verified:
                if instance.payment_type == 'REGISTRATION':
                    application.payment_completed = True
                    logger.info(f"Registration fee marked as paid for application {application.application_number}")
                elif instance.payment_type == 'WELFARE':
                    application.welfare_fee_paid = True
                    logger.info(f"Welfare fee marked as paid for application {application.application_number}")

                # If both fees are paid, log it
                if application.payment_completed:
                    logger.info(f"All fees paid for application {application.application_number}")

                application.save()


    except Exception as e:
        logger.error(f"Error updating payment status for application {instance.application.application_number}: {str(e)}")
        raise

@receiver(post_save, sender=MembershipApplication)
def handle_application_approval(sender, instance, created, **kwargs):
    """
    When an application is approved and all payments are verified, create or update member profile
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
                    # Create loan plans for each loan type
                    for loan_type, _ in LoanPlan.PLAN_TYPES:
                        try:
                            # Check if plan already exists
                            if not LoanPlan.objects.filter(user=instance.user, plan_type=loan_type).exists():
                                # Get default tenure for this loan type
                                default_tenure = LoanTenure.objects.filter(plan_type=loan_type).first()
                                if not default_tenure:
                                    logger.warning(f"No default tenure found for {loan_type}. Skipping plan creation.")
                                    continue

                                LoanPlan.objects.create(
                                    user=instance.user,
                                    plan_type=loan_type,
                                    min_amount=0,  # These will be set by admin later
                                    max_amount=0,  # These will be set by admin later
                                    description=f"Default {loan_type.replace('_', ' ').title()} Plan",
                                    requirements="Please contact admin for loan requirements",
                                    loan_tenure=default_tenure  # Required field
                                )
                                logger.info(f"Created {loan_type} loan plan for user {instance.user.username}")
                        except Exception as e:
                            logger.error(f"Error creating {loan_type} loan plan for user {instance.user.username}: {str(e)}")

                    # Create savings plans for each savings type
                    for plan_type, _ in SavingsPlan.PLAN_CHOICES:
                        try:
                            # Check if plan already exists
                            if not SavingsPlan.objects.filter(user=instance.user, plan_type=plan_type).exists():
                                # Get payment account for this plan type
                                payment_account = PaymentAccount.objects.filter(plan_type=plan_type).first()
                                if not payment_account:
                                    logger.warning(f"No payment account found for {plan_type}. Skipping plan creation.")
                                    continue

                                SavingsPlan.objects.create(
                                    user=instance.user,
                                    plan_type=plan_type,
                                    amount=0,  # Initial amount
                                    payment_account=payment_account,  # Required field
                                    status='active',
                                    maturity_date=timezone.now().date() + timezone.timedelta(days=730)  # 2 years restriction
                                )
                                logger.info(f"Created {plan_type} savings plan for user {instance.user.username}")
                        except Exception as e:
                            logger.error(f"Error creating {plan_type} savings plan for user {instance.user.username}: {str(e)}")

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
def handle_member_status_changes(sender, instance, created, **kwargs):
    """
    Handle member status changes and related updates
    """
    try:
        with transaction.atomic():
            if instance.blacklisted and not instance.blacklist_reason:
                logger.warning(f"Member {instance.membership_number} was blacklisted without a reason")

            if not instance.is_active and instance.application and instance.application.status == 'APPROVED':
                logger.warning(f"Member {instance.membership_number} was deactivated while having an approved application")

    except Exception as e:
        logger.error(f"Error handling member {instance.membership_number} status changes: {str(e)}")
        raise