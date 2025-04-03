from django.shortcuts import render
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, View
from .models import *
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from .forms import CreateDepositForm, PaymentAccountForm, SavingsPlanForm, SavingsTransactionForm
import requests, json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from decimal import Decimal
import logging
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils import timezone
from django.http import FileResponse
from .utils import generate_savings_receipt_pdf
from django.contrib.auth.mixins import UserPassesTestMixin
import uuid
from django.db import transaction
from decimal import Decimal, InvalidOperation, ROUND_DOWN
# Set up logger
logger = logging.getLogger(__name__)


# List all savings plans for the member
class SavingsPlansListView(LoginRequiredMixin, ListView):
    """
    This view lists all savings plans for a member.

    It displays a list of all savings plans for the member, along with the total savings across all plans and the total interest earned across all plans.
    """
    model = SavingsPlan
    template_name = 'savings/plans_list.html'
    context_object_name = 'savings_plans'
    paginate_by = 20  # Add pagination for transactions

    def get_queryset(self):
        try:
            return SavingsPlan.objects.filter(
                user=self.request.user,
                status='active'
            ).select_related('plan_type')
        except Exception as e:
            logger.error(f"Error fetching savings plans for user {self.request.user.username}: {str(e)}")
            return SavingsPlan.objects.none()

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)

            # Calculate totals
            plans = context['savings_plans']
            context['total_savings'] = sum(
                SavingsTransaction.objects.filter(
                    savings_plan=plan,
                    transaction_type='deposit',
                    status='approved'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                for plan in plans
            )

            # Calculate interest for each plan
            total_interest = Decimal('0')
            for plan in plans:
                try:
                    total_interest += plan.calculate_interest()
                except Exception as e:
                    logger.error(f"Error calculating interest for plan {plan.id}: {str(e)}")

            context['total_interest'] = total_interest

            # Get all user transactions with pagination
            transactions = SavingsTransaction.objects.filter(
                savings_plan__user=self.request.user
            ).select_related('savings_plan').order_by('-transaction_date')

            paginator = Paginator(transactions, self.paginate_by)
            page = self.request.GET.get('page')
            context['user_transactions'] = paginator.get_page(page)

            # Count pending transactions
            context['pending_transactions'] = transactions.filter(status='pending').count()

            return context
        except Exception as e:
            logger.error(f"Error in SavingsPlansListView context for user {self.request.user.username}: {str(e)}")
            return super().get_context_data(**kwargs)


class SavingsPlanDetailView(LoginRequiredMixin, DetailView):
    model = SavingsPlan
    template_name = 'savings/plan_details.html'
    context_object_name = 'plan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan_type_details'] = {
            'minimum_balance': self.object.plan_type.minimum_balance,
            'interest_rate': self.object.plan_type.default_interest_rate,
            'maturity_date': self.object.maturity_date,
        }
        # Calculate interest
        context['interest_earned'] = self.object.calculate_interest()
        # Get payment account details
        context['payment_details'] = self.object.payment_account

        # Get transactions for this specific savings plan and user
        transactions = SavingsTransaction.objects.filter(
            savings_plan=self.object,
            savings_plan__user=self.request.user
        ).select_related('savings_plan').order_by('-transaction_date')

        # Paginate transactions
        paginator = Paginator(transactions, 10)  # Show 10 transactions per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['transactions'] = page_obj

        # Calculate totals for this plan (using full queryset, not paginated)
        deposits = transactions.filter(
            transaction_type='deposit',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        withdrawals = transactions.filter(
            transaction_type='withdrawal',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        context['total_deposits'] = deposits
        context['total_withdrawals'] = withdrawals

        return context


# class CreateSavingsPlanView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
#     model = SavingsPlan
#     template_name = 'savings/create_plan.html'
#     fields = ['plan_type']
#     success_url = reverse_lazy('savings:plans_list')
#     success_message = "Your savings plan has been created successfully!"

#     def get_form(self, form_class=None):
#         form = super().get_form(form_class)
#         # Only show plan types that have payment accounts
#         available_plans = PaymentAccount.objects.values_list('plan_type', flat=True)
#         form.fields['plan_type'].choices = [
#             choice for choice in form.fields['plan_type'].choices
#             if choice[0] in available_plans
#         ]
#         return form

#     def form_valid(self, form):
#         try:
#             form.instance.user = self.request.user
#             # Get corresponding payment account
#             form.instance.payment_account = PaymentAccount.objects.get(
#                 plan_type=form.instance.plan_type
#             )
#             return super().form_valid(form)
#         except PaymentAccount.DoesNotExist:
#             messages.error(self.request, "This savings plan type is currently unavailable. Please contact admin.")
#             return self.form_invalid(form)

class CreateSavingsPlanView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = SavingsPlan
    template_name = 'savings/create_plan.html'
    form_class = SavingsPlanForm
    success_url = reverse_lazy('savings:plans_list')
    success_message = "Your savings plan has been created successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only show active plan types that have payment accounts
        context['available_plans'] = SavingsPlanType.objects.filter(
            is_active=True,
            payment_accounts__isnull=False
        ).distinct()
        return context

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            plan_type = form.cleaned_data['plan_type']

            # Get corresponding payment account
            payment_account = PaymentAccount.objects.filter(
                plan_type=plan_type,
            ).first()

            if not payment_account:
                messages.error(self.request, "This savings plan type is currently unavailable. Please contact admin.")
                return self.form_invalid(form)

            form.instance.payment_account = payment_account
            form.instance.interest_rate = plan_type.default_interest_rate

            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error creating savings plan: {str(e)}")
            return self.form_invalid(form)

class CreateDepositView(LoginRequiredMixin, CreateView):
    model = SavingsTransaction
    template_name = 'savings/create_deposit.html'
    form_class = CreateDepositForm
    # fields = ['amount', 'payment_proof', 'payment_account']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['savings_plan'] = get_object_or_404(
            SavingsPlan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan'] = get_object_or_404(
            SavingsPlan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return context

    # def form_valid(self, form):
    #     plan = get_object_or_404(
    #         SavingsPlan,
    #         id=self.kwargs['pk'],
    #         user=self.request.user
    #     )
    #     form.instance.savings_plan = plan
    #     form.instance.transaction_type = 'deposit'
    #     form.instance.reference_number = f"DEP-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    #     return super().form_valid(form)

    def form_valid(self, form):
        plan = get_object_or_404(
            SavingsPlan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        form.instance.savings_plan = plan
        form.instance.transaction_type = 'deposit'
        form.instance.reference_number = f"DEP-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        response = super().form_valid(form)

        # Add detailed success message
        amount = form.instance.amount
        ref_number = form.instance.reference_number
        messages.success(
            self.request,
            f'Your deposit of ₦{amount:,.2f} has been submitted successfully!\n'
            f'Reference Number: {ref_number}\n'
            f'Status: Pending Admin Verification\n'
            'Your transaction will be processed once the payment proof is verified. '
            'You will be notified when the deposit is approved.'
        )

        # Log the transaction
        logger.info(
            f"New deposit submitted - Amount: ₦{amount:,.2f}, "
            f"Reference: {ref_number}, Plan: {plan.plan_type}"
        )

        return response


    def get_success_url(self):
        # Redirect to the plan details page after a successful deposit
        return reverse('savings:plan_details', kwargs={'pk': self.kwargs['pk']})


# class PaystackDepositView(LoginRequiredMixin, View):
#     def post(self, request, pk):
#         plan = get_object_or_404(SavingsPlan, id=pk, user=request.user)
#         # amount = request.POST.get('amount')

#         try:
#             data = json.loads(request.body)
#             amount = data.get('amount')
#             # Convert amount to kobo (Paystack uses kobo)
#             amount_in_kobo = int(float(amount) * 100)

#             # Payment description including bank details
#             payment_description = (
#                 f"Deposit to {plan.get_plan_type_display()} Savings Plan - "
#                 f"Bank: {plan.payment_account.bank_name}, "
#                 f"Account: {plan.payment_account.account_name}, "
#                 f"Number: {plan.payment_account.account_number}"
#             )

#             # Initialize Paystack transaction
#             url = 'https://api.paystack.co/transaction/initialize'
#             headers = {
#                 'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
#                 'Content-Type': 'application/json'
#             }
#             data = {
#                 'email': request.user.email,
#                 'amount': amount_in_kobo,
#                 'callback_url': request.build_absolute_uri(reverse('savings:paystack_callback')),
#                 'reference': f"DEP-{plan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
#                 'metadata': {
#                     'plan_id': plan.id,
#                     'plan_type': plan.plan_type,
#                     'payment_account': {
#                         'bank': plan.payment_account.bank_name,
#                         'name': plan.payment_account.account_name,
#                         'number': plan.payment_account.account_number
#                     }
#                 },
#                 'description': payment_description
#             }

#             response = requests.post(url, headers=headers, json=data)
#             response_data = response.json()

#             if response_data['status']:
#                 return JsonResponse({
#                     'status': 'success',
#                     'authorization_url': response_data['data']['authorization_url']
#                 })
#             else:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'Could not initialize payment'
#                 }, status=400)

#         except Exception as e:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)


class PaystackDepositView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            # Validate plan exists and belongs to user
            plan = get_object_or_404(
                SavingsPlan,
                id=pk,
                user=request.user,
                status='active'
            )

            # Parse and validate request data
            try:
                data = json.loads(request.body)
                amount = data.get('amount')
                if not amount:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Amount is required'
                    }, status=400)

                # Validate amount is numeric and positive
                amount = Decimal(str(amount))
                if amount <= 0:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Amount must be greater than 0'
                    }, status=400)

                # Convert to kobo (Paystack uses kobo)
                amount_in_kobo = int(amount * 100)

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid amount format'
                }, status=400)

            # Validate Paystack configuration
            if not all([settings.PAYSTACK_SECRET_KEY, settings.PAYSTACK_BASE_URL]):
                logger.error("Paystack configuration missing")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment service configuration error'
                }, status=500)

            # Generate unique reference
            reference = f"DEP-{plan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"

            # Payment description
            payment_description = (
                f"Deposit to {plan.plan_type.display_name} - "
                f"Bank: {plan.payment_account.bank_name}, "
                f"Account: {plan.payment_account.account_name}"
            )

            # Initialize Paystack transaction
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }

            payload = {
                'email': request.user.email,
                'amount': amount_in_kobo,
                'callback_url': request.build_absolute_uri(reverse('savings:paystack_callback')),
                'reference': reference,
                'metadata': {
                    'plan_id': plan.id,
                    'plan_type': plan.plan_type.name,
                    'user_id': request.user.id,
                    'payment_account': {
                        'bank': plan.payment_account.bank_name,
                        'name': plan.payment_account.account_name,
                        'number': plan.payment_account.account_number
                    }
                },
                'description': payment_description
            }

            # Make request to Paystack
            try:
                response = requests.post(
                    f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                response_data = response.json()

            except requests.RequestException as e:
                logger.error(f"Paystack API error: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unable to initialize payment. Please try again.'
                }, status=503)

            if not response_data.get('status'):
                logger.error(f"Payment verification failed. Status: {response_data.get('data', {}).get('status')}")
                messages.error(request, 'Payment verification failed. Please try again or contact support.')
                return redirect('savings:plans_list')

            # Log successful initialization
            logger.info(
                f"Payment initialized - Amount: ₦{amount:,.2f}, "
                f"Reference: {reference}, Plan: {plan.plan_type.name}"
            )

            return JsonResponse({
                'status': 'success',
                'authorization_url': response_data['data']['authorization_url'],
                'reference': reference
            })

        except Exception as e:
            logger.error(f"Unexpected error in PaystackDepositView: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=500)

# class PaystackCallbackView(LoginRequiredMixin, View):
#     def get(self, request):
#         reference = request.GET.get('reference')
#         logger.info(f"Received Paystack callback for reference: {reference}")

#         try:
#             # Verify transaction
#             url = f'https://api.paystack.co/transaction/verify/{reference}'
#             headers = {
#                 'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
#             }
#             response = requests.get(url, headers=headers)
#             response_data = response.json()

#             logger.info(f"Paystack verification response: {response_data}")

#             if response_data['status'] and response_data['data']['status'] == 'success':
#                 # Extract plan_id from reference
#                 try:
#                     ref_parts = reference.split('-')
#                     plan_id = int(ref_parts[1])
#                     plan = SavingsPlan.objects.get(id=plan_id)
#                 except (IndexError, ValueError, SavingsPlan.DoesNotExist) as e:
#                     logger.error(f"Error extracting plan_id from reference: {str(e)}")
#                     messages.error(request, 'Invalid transaction reference. Please contact support.')
#                     return redirect('savings:plans_list')

#                 try:
#                     # Convert amount from kobo to Naira and ensure it's a decimal
#                     amount = Decimal(str(response_data['data']['amount'])) / Decimal('100')

#                     # Create transaction record
#                     transaction = SavingsTransaction.objects.create(
#                         savings_plan=plan,
#                         transaction_type='deposit',
#                         amount=amount,
#                         status='approved',  # Auto-approve online payments
#                         reference_number=reference,
#                         description=f'Online payment via Paystack - {reference}',
#                         approval_date=timezone.now()
#                     )

#                     logger.info(f"Successfully created transaction: {transaction.id} for plan: {plan_id}")
#                     messages.success(request, f'Payment successful! Your deposit of ₦{amount:,.2f} has been processed.')
#                     return redirect('savings:plan_details', pk=plan_id)

#                 except (ValueError, Decimal.InvalidOperation) as e:
#                     logger.error(f"Error processing amount: {str(e)}")
#                     messages.error(request, 'Error processing payment amount. Please contact support.')
#                     return redirect('savings:plans_list')

#             else:
#                 logger.error(f"Payment verification failed. Status: {response_data.get('data', {}).get('status')}")
#                 messages.error(request, 'Payment verification failed. Please try again or contact support.')
#                 return redirect('savings:plans_list')

#         except Exception as e:
#             logger.error(f"Error in PaystackCallbackView: {str(e)}")
#             messages.error(request, f'Error processing payment: {str(e)}')
#             return redirect('savings:plans_list')


class PaystackCallbackView(LoginRequiredMixin, View):
    def get(self, request):
        reference = request.GET.get('reference')

        if not reference:
            messages.error(request, 'No transaction reference provided')
            return redirect('savings:plans_list')

        logger.info(f"Received Paystack callback for reference: {reference}")

        try:
            # Extract plan_id from reference
            try:
                plan_id = int(reference.split('-')[1])
            except (IndexError, ValueError) as e:
                logger.error(f"Invalid reference format: {str(e)}")
                messages.error(request, 'Invalid transaction reference format')
                return redirect('savings:plans_list')

            # Verify plan exists and belongs to user
            try:
                plan = SavingsPlan.objects.get(
                    id=plan_id,
                    user=request.user,
                    status='active'
                )
            except SavingsPlan.DoesNotExist:
                logger.error(f"Plan not found or unauthorized: {plan_id}")
                messages.error(request, 'Invalid savings plan or unauthorized access')
                return redirect('savings:plans_list')

            # Check if transaction already exists
            if SavingsTransaction.objects.filter(reference_number=reference).exists():
                logger.warning(f"Duplicate transaction callback received: {reference}")
                messages.warning(request, 'This transaction has already been processed')
                return redirect('savings:plan_details', pk=plan_id)

            # Verify transaction with Paystack
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }

            try:
                response = requests.get(
                    f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                response_data = response.json()

            except requests.RequestException as e:
                logger.error(f"Paystack API error: {str(e)}")
                messages.error(request, 'Unable to verify payment. Please try again later.')
                return redirect('savings:plans_list')

            if not response_data.get('status'):
                logger.error(f"Payment verification failed: {response_data.get('message')}")
                messages.error(request, 'Payment verification failed. Please try again or contact support.')
                return redirect('savings:plans_list')

            # Verify payment status
            payment_status = response_data['data']['status']
            if payment_status != 'success':
                logger.warning(f"Payment not successful. Status: {payment_status}")
                messages.warning(request, f'Payment {payment_status}. Please try again or contact support.')
                return redirect('savings:plans_list')

            try:
                # Convert amount from kobo to Naira
                amount_kobo = str(response_data['data']['amount'])
                amount = Decimal(amount_kobo) / Decimal('100')

                if amount <= 0:
                    raise ValueError("Invalid amount")

                # Create transaction in atomic transaction
                with transaction.atomic():
                    # Create transaction record with approved status
                    # The signal handler will update the plan balance
                    transaction_obj = SavingsTransaction.objects.create(
                        savings_plan=plan,
                        transaction_type='deposit',
                        amount=amount,
                        status='approved',  # This will trigger the signal handler
                        reference_number=reference,
                        description=f'Online payment via Paystack - {reference}',
                        approval_date=timezone.now(),
                        payment_method='paystack',
                        payment_details={
                            'paystack_reference': reference,
                            'payment_channel': response_data['data'].get('channel'),
                            'bank': response_data['data'].get('authorization', {}).get('bank'),
                            'card_type': response_data['data'].get('authorization', {}).get('card_type')
                        }
                    )

                    logger.info(f"Successfully processed transaction {reference} for plan {plan_id}")
                    messages.success(
                        request,
                        f'Payment successful! Your deposit of ₦{amount:,.2f} has been processed.'
                    )
                    return redirect('savings:plan_details', pk=plan_id)

            except (ValueError, InvalidOperation) as e:
                logger.error(f"Error processing amount: {str(e)}")
                messages.error(request, 'Error processing payment amount')
                return redirect('savings:plans_list')

        except Exception as e:
            logger.error(f"Unexpected error in PaystackCallbackView: {str(e)}")
            messages.error(request, 'An unexpected error occurred. Please contact support.')
            return redirect('savings:plans_list')



class CreateWithdrawalView(LoginRequiredMixin, CreateView):
    model = SavingsTransaction
    template_name = 'savings/create_withdrawal.html'
    fields = ['amount', 'description']

    def get_plan(self):
        return get_object_or_404(
            SavingsPlan,
            id=self.kwargs['pk'],
            user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan'] = self.get_plan()
        return context

    def form_valid(self, form):
        plan = self.get_plan()

        # Check withdrawal restrictions
        if plan.maturity_date and timezone.now().date() < plan.maturity_date:
            messages.error(
                self.request,
                f'Cannot withdraw from this savings plan before maturity date ({plan.maturity_date.strftime("%B %d, %Y")})'
            )
            return self.form_invalid(form)

        if form.instance.amount > plan.amount:
            messages.error(
                self.request,
                f'Withdrawal amount (₦{form.instance.amount:,.2f}) exceeds available balance (₦{plan.amount:,.2f})'
            )
            return self.form_invalid(form)

        form.instance.savings_plan = plan
        form.instance.transaction_type = 'withdrawal'
        form.instance.reference_number = f"WIT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        form.instance.status = 'pending'  # Ensure status is set to pending
        response = super().form_valid(form)

        amount = form.instance.amount
        ref_number = form.instance.reference_number

        # Format success message for better readability
        message_parts = [
            f'Your withdrawal of ₦{amount:,.2f} has been submitted successfully!',
            f'Reference Number: {ref_number}',
            'Status: Pending Admin Verification',
            'Your transaction will be processed once verified.',
            'You will be notified when the withdrawal is approved.'
        ]
        messages.success(self.request, '\n'.join(message_parts))

        # Log the transaction
        logger.info(
            f"New withdrawal submitted - Amount: ₦{amount:,.2f}, "
            f"Reference: {ref_number}, Plan: {plan.plan_type}"
        )
        return response

    def get_success_url(self):
        # Redirect to the plan details page after a successful withdrawal
        return reverse('savings:plan_details', kwargs={'pk': self.kwargs['pk']})


class UserTransactionListView(LoginRequiredMixin, ListView):
    model = SavingsTransaction
    template_name = 'savings/dashboard/user_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        # Here we just filter by the current user and no savings_plan filter.
        return SavingsTransaction.objects.filter(user=self.request.user).order_by('-transaction_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed, such as the number of pending transactions, etc.
        context['pending_transactions'] = self.get_queryset().filter(status='pending').count()
        return context


class TransactionListView(LoginRequiredMixin, ListView):
    model = SavingsTransaction
    template_name = 'savings/transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        return SavingsTransaction.objects.filter(
            savings_plan__user=self.request.user
        ).select_related('savings_plan').order_by('-transaction_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_transactions'] = self.get_queryset().filter(status='pending').count()
        return context


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = SavingsTransaction
    template_name = 'savings/transaction_detail.html'
    context_object_name = 'plan'

    def get_queryset(self):
        return SavingsTransaction.objects.filter(
            savings_plan__user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add plan type for template display
        context['savings'] = self.object.savings_plan

        # Add plan type specific information
        if self.object.savings_plan.plan_type == 'Investment':
            context['days_to_maturity'] = (self.object.savings_plan.maturity_date - timezone.now().date()).days if self.object.savings_plan.maturity_date else None
            context['total_investment'] = SavingsPlan.objects.filter(
                user=self.request.user,
                plan_type='Investment'
            ).aggregate(total=Sum('amount'))['total'] or 0
        elif self.object.savings_plan.plan_type == 'Savings':
            context['total_savings'] = SavingsPlan.objects.filter(
                user=self.request.user,
                plan_type='Savings'
            ).aggregate(total=Sum('amount'))['total'] or 0
        elif self.object.savings_plan.plan_type == 'Children':
            context['total_children_savings'] = SavingsPlan.objects.filter(
                user=self.request.user,
                plan_type='Children'
            ).aggregate(total=Sum('amount'))['total'] or 0

        return context



class DownloadTransactionReceiptView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            transaction = SavingsTransaction.objects.get(
                pk=pk,
                savings_plan__user=request.user,
                status='approved'  # Only allow downloading receipts for approved transactions
            )

            # Generate PDF
            pdf_buffer = generate_savings_receipt_pdf(transaction)

            # Create response
            response = FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=f'savings_receipt_{transaction.reference_number}.pdf'
            )
            return response

        except SavingsTransaction.DoesNotExist:
            messages.error(request, "Transaction not found or not approved.")
            return redirect('savings:plans_list')



###########################################################################
# ADMIN VIEWS
#######################################################



# Admin CRUD Views for SavingsTransaction
class AdminTransactionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = SavingsTransaction
    template_name = 'savings/admin/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related('savings_plan', 'savings_plan__user').order_by('-transaction_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Savings Transactions'
        context['pending_count'] = self.model.objects.filter(status='pending').count()
        return context


class AdminTransactionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = SavingsTransaction
    template_name = 'savings/admin/transaction_detail.html'
    context_object_name = 'transaction'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Transaction: {self.object.reference_number}'
        return context


class AdminTransactionUpdateView(UserPassesTestMixin, UpdateView):
    model = SavingsTransaction
    form_class = SavingsTransactionForm
    template_name = 'savings/admin/transaction_form.html'
    success_message = "Transaction was updated successfully!"

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': self.success_message
            })
        messages.success(self.request, self.success_message)
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors below.',
                'errors': form.errors
            })
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('savings:admin_transaction_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Transaction'
        context['transaction'] = self.object
        return context