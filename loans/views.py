from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from decimal import Decimal
import json
import logging
from django.forms import formset_factory
import requests
from django.conf import settings
from members.models import Member
from decimal import Decimal
from .utils import check_loan_eligibility
from .models import (
    LoanPlan, LoanApplication, Loan, LoanTransaction,
    Guarantor, LoanPlanType
)
from .forms import (
    LoanApplicationForm, GuarantorForm, LoanRepaymentForm, LoanApplicationForm2,LoanForm, LoanTransactionForm
)

logger = logging.getLogger(__name__)

# class LoanDashboardView(LoginRequiredMixin, ListView):
#     """Dashboard view showing user's loans and applications"""
#     model = LoanApplication
#     template_name = 'loans/dashboard.html'
#     context_object_name = 'loan_applications'

#     def get_queryset(self):
#         return LoanApplication.objects.filter(user=self.request.user).order_by('-application_date')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['active_loans'] = Loan.objects.filter(
#             user=self.request.user,
#             status='active'
#         )
#         context['total_loan_balance'] = sum(loan.loan_balance for loan in context['active_loans'])
#         context['pending_applications'] = self.get_queryset().filter(status='pending').count()

#         # Recent transactions
#         context['recent_transactions'] = LoanTransaction.objects.filter(
#             loan__user=self.request.user
#         ).order_by('-payment_date')[:5]

#         return context

#


class LoanPlansListView(LoginRequiredMixin, ListView):
    """View to list all available loan plans"""
    model = LoanPlan
    template_name = 'loans/plans_list.html'
    context_object_name = 'loan_plans'

    def get_queryset(self):
        return LoanPlan.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all loans for the user
        user_loans = Loan.objects.filter(user=self.request.user)

        # Get total active loans
        context['active_loans'] = user_loans.filter(status='active').count()

        # Get total loan amount
        context['total_loan_amount'] = user_loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or 0

        # Get user's transactions
        user_transactions = LoanTransaction.objects.filter(
            loan__user=self.request.user
        ).order_by('-payment_date')

        # Paginate the transactions
        paginator = Paginator(user_transactions, 20)
        page_number = self.request.GET.get('page')
        context['user_transactions'] = paginator.get_page(page_number)

        # Get pending transactions count
        context['pending_transactions'] = user_transactions.filter(status='pending').count()

        # Get loan applications
        context['pending_applications'] = LoanApplication.objects.filter(
            user=self.request.user,
            status='pending'
        ).count()

        return context

class LoanPlanDetailView(LoginRequiredMixin, DetailView):
    """View to display details of a specific loan plan"""
    model = LoanPlan
    template_name = 'loans/plan_details.html'
    context_object_name = 'plan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.get_object()

        # Get loan applications for this plan
        loan_applications = LoanApplication.objects.filter(
            loan_plan=plan,
            user=self.request.user
        ).order_by('-application_date')

        # Paginate loan applications
        paginator = Paginator(loan_applications, 10)
        page_number = self.request.GET.get('applications_page')
        context['loan_applications'] = paginator.get_page(page_number)

        # Get loans for this plan
        loans = Loan.objects.filter(
            loan_plan=plan,
            user=self.request.user
        ).order_by('-created_at')

        # Paginate loans
        paginator = Paginator(loans, 10)
        page_number = self.request.GET.get('loans_page')
        context['loans'] = paginator.get_page(page_number)

        # Get loan transactions for this plan
        loan_transactions = LoanTransaction.objects.filter(
            loan__user=self.request.user,
            loan__loan_plan__plan_type=plan.plan_type
        ).select_related('loan', 'loan__loan_plan').order_by('-payment_date')

        # Paginate transactions
        paginator = Paginator(loan_transactions, 20)
        page_number = self.request.GET.get('transactions_page')
        page_obj = paginator.get_page(page_number)

        # Add transaction data to context
        context['loan_transactions'] = page_obj
        context['pending_transactions'] = loan_transactions.filter(status='pending').count()

        # Add plan type for template display
        context['plan_type'] = plan.plan_type.name

        # Get pending loan applications
        context['pending_applications'] = LoanApplication.objects.filter(
            user=self.request.user,
            loan_plan__plan_type=plan.plan_type.name,
            status='under_review'
        ).count()

        # Add plan type specific information
        if plan.plan_type == 'emergency':
            context['total_emergency_loans'] = Loan.objects.filter(
                user=self.request.user,
                loan_plan__plan_type=plan.plan_type.name,
                status='active'
            ).aggregate(total=Sum('loan_amount'))['total'] or 0

        elif plan.plan_type == 'normal':
            context['total_normal_loans'] = Loan.objects.filter(
                user=self.request.user,
                loan_plan__plan_type=plan.plan_type.name,
                status='active'
            ).aggregate(total=Sum('loan_amount'))['total'] or 0

        elif plan.plan_type == 'long_term':
            context['total_long_term_loans'] = Loan.objects.filter(
                user=self.request.user,
                loan_plan__plan_type=plan.plan_type.name,
                status='active'
            ).aggregate(total=Sum('loan_amount'))['total'] or 0

        # Add requirements
        context['requirements'] = plan.requirements

        return context

GuarantorFormSet = formset_factory(GuarantorForm, extra=2)

class LoanApplicationCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """View to create a new loan application"""
    model = LoanApplication
    form_class = LoanApplicationForm
    template_name = 'loans/create_application.html'
    success_message = "Your loan application has been submitted successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['loan_plan'] = get_object_or_404(LoanPlan, pk=self.kwargs.get('plan_pk'))
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loan_plan'] = get_object_or_404(LoanPlan, pk=self.kwargs.get('plan_pk'))

        if self.request.POST:
            context['guarantor_formset'] = GuarantorFormSet(
                data=self.request.POST,
                prefix='guarantors'
            )
        else:
            context['guarantor_formset'] = GuarantorFormSet(
                prefix='guarantors'
            )

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        guarantor_formset = context['guarantor_formset']

        if guarantor_formset.is_valid():
            # Set user, loan plan, and tenure before saving the form
            form.instance.user = self.request.user
            loan_plan = get_object_or_404(LoanPlan, pk=self.kwargs.get('plan_pk'))
            form.instance.loan_plan = loan_plan
            form.instance.tenure = loan_plan.loan_tenure  # Set the tenure from loan plan
            self.object = form.save()

            # Save each guarantor form
            for guarantor_form in guarantor_formset:
                if guarantor_form.is_valid() and guarantor_form.has_changed():
                    guarantor = guarantor_form.save(commit=False)
                    guarantor.loan_application = self.object
                    guarantor.save()

            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('loans:application_detail', kwargs={'pk': self.object.pk})

class LoanApplicationDetailView(LoginRequiredMixin, DetailView):
    """View to show loan application details"""
    model = LoanApplication
    template_name = 'loans/application_detail.html'
    context_object_name = 'application'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()

        # Add loan plan details
        context['loan_plan'] = application.loan_plan
        context['tenure'] = application.tenure

        # Calculate loan details using simple interest (same as in signals.py)
        interest_rate = Decimal(str(application.tenure.interest_rate)) / Decimal('100')
        months_ratio = Decimal(str(application.tenure.months)) / Decimal('12')
        loan_amount = Decimal(str(application.loan_amount))

        # Calculate total interest and monthly payment
        total_interest = loan_amount * interest_rate * months_ratio
        total_payable = loan_amount + total_interest
        monthly_payment = total_payable / Decimal(str(application.tenure.months))

        context['monthly_payment'] = round(monthly_payment, 2)
        context['total_payable'] = round(total_payable, 2)
        context['total_interest'] = round(total_interest, 2)

        # Get guarantors using the correct related name
        context['guarantors'] = application.loan_guarantors.all()

        # Check eligibility if payment is made
        if application.has_paid:
            try:
                member = Member.objects.get(user=self.request.user)
                # Convert loan_amount to Decimal if it's not already
                loan_amount = Decimal(str(application.loan_amount))
                context['eligibility_result'] = check_loan_eligibility(member, loan_amount)
            except Member.DoesNotExist:
                context['eligibility_result'] = {
                    "decision": "rejected",
                    "reasons": ["User is not a registered member."]
                }

        # Add empty notifications context for template
        context['latest_notifications'] = []

        if application.status == 'approved':
            context['loan'] = Loan.objects.filter(application=application).first()

        return context

class LoanDetailView(LoginRequiredMixin, DetailView):
    """View to display details of a specific loan and related information"""
    model = Loan
    template_name = 'loans/loan_detail.html'
    context_object_name = 'loan'

    def get_queryset(self):
        """Optimize initial loan query with related fields"""
        return Loan.objects.select_related(
            'user',
            'loan_plan',
            'loan_plan__loan_tenure',
            'application'
        ).filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()

        # Get all active loans for this user of the same plan type
        active_loans = Loan.objects.filter(
            user=self.request.user,
            loan_plan__plan_type=loan.loan_plan.plan_type,
            status='active'
        )

        # Use single query to get all aggregates
        loan_totals = active_loans.aggregate(
            total_amount=Sum('loan_amount'),
            total_payable=Sum('total_payable'),
            count=Count('id')
        )

        # Add loan statistics to context
        context.update({
            'active_loans_count': loan_totals['count'] or 0,
            'total_loan_amount': loan_totals['total_amount'] or 0,
            'total_payable': loan_totals['total_payable'] or 0,
            'interest_rate': loan.loan_plan.loan_tenure.interest_rate,
            'tenure_months': loan.loan_plan.loan_tenure.months
        })

        # Get loan transactions with efficient querying
        transactions = LoanTransaction.objects.filter(
            loan=loan
        ).select_related(
            'loan'
        ).order_by('-payment_date')

        # Add transaction summary
        transaction_summary = transactions.aggregate(
            total_paid=Sum('amount', filter=Q(
                transaction_type='repayment',
                status='approved'
            )),
            pending_amount=Sum('amount', filter=Q(
                transaction_type='repayment',
                status='pending'
            ))
        )

        context.update({
            'total_paid': transaction_summary['total_paid'] or 0,
            'pending_amount': transaction_summary['pending_amount'] or 0,
            'remaining_balance': loan.loan_balance,
            'payment_progress': loan.payment_progress
        })

        # Paginate transactions
        paginator = Paginator(transactions, 20)
        page_number = self.request.GET.get('page')
        context['transactions'] = paginator.get_page(page_number)

        # Add payment schedule
        context['payment_schedule'] = loan.get_payment_schedule()

        # Add next payment information
        if loan.status == 'active':
            context.update({
                'next_payment_date': loan.next_payment_date,
                'next_payment_amount': loan.monthly_payment,
                'payment_status': loan.payment_status,
                'remaining_installments': loan.get_remaining_installments()
            })
        else:
            context.update({
                'next_payment_date': None,
                'next_payment_amount': None,
                'payment_status': None,
                'remaining_installments': None
            })
        return context

class GuarantorCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """View to add a guarantor to a loan application"""
    model = Guarantor
    form_class = GuarantorForm
    template_name = 'loans/add_guarantor.html'
    success_message = "Guarantor has been added successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application'] = get_object_or_404(
            LoanApplication,
            pk=self.kwargs.get('application_pk'),
            user=self.request.user
        )
        return context

    def form_valid(self, form):
        application = get_object_or_404(
            LoanApplication,
            pk=self.kwargs.get('application_pk'),
            user=self.request.user
        )
        guarantor = form.save()
        application.guarantors.add(guarantor)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('loans:application_detail',
                      kwargs={'pk': self.kwargs.get('application_pk')})


class LoanRepaymentView(LoginRequiredMixin, CreateView):
    model = LoanTransaction
    template_name = 'loans/loan_detail.html'
    form_class = LoanRepaymentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['loan'] = get_object_or_404(
            Loan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loan'] = get_object_or_404(
            Loan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return context

    def form_valid(self, form):
        loan = get_object_or_404(
            Loan,
            id=self.kwargs['pk'],
            user=self.request.user
        )
        form.instance.loan = loan
        form.instance.transaction_type = 'repayment'
        form.instance.status = 'pending'
        form.instance.reference_number = f"REP-{loan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        response = super().form_valid(form)

        # Add detailed success message
        amount = form.instance.amount
        ref_number = form.instance.reference_number
        messages.success(
            self.request,
            f'Your loan repayment of ₦{amount:,.2f} has been submitted successfully!\n'
            f'Reference Number: {ref_number}\n'
            f'Status: Pending Admin Verification\n'
            'Your payment will be processed once the payment proof is verified. '
            'You will be notified when the repayment is approved.'
        )

        # Log the transaction
        logger.info(
            f"New loan repayment submitted - Amount: ₦{amount:,.2f}, "
            f"Reference: {ref_number}, Loan ID: {loan.id}"
        )

        return response

    def get_success_url(self):
        return reverse('loans:loan_detail', kwargs={'pk': self.kwargs['pk']})


# class LoanRepaymentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
#     """View to create a loan repayment"""
#     model = LoanTransaction
#     form_class = LoanRepaymentForm
#     template_name = 'loans/create_repayment.html'
#     success_message = "Your repayment has been submitted successfully!"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['loan'] = get_object_or_404(
#             Loan,
#             pk=self.kwargs.get('loan_pk'),
#             user=self.request.user
#         )
#         return context

#     def form_valid(self, form):
#         loan = get_object_or_404(
#             Loan,
#             pk=self.kwargs.get('loan_pk'),
#             user=self.request.user
#         )
#         form.instance.loan = loan
#         form.instance.transaction_type = 'repayment'
#         return super().form_valid(form)

#     def get_success_url(self):
#         return reverse('loans:loan_detail',
#                       kwargs={'pk': self.kwargs.get('loan_pk')})

# class UserTransactionListView(LoginRequiredMixin, ListView):
#     """View to list all transactions for a user"""
#     model = LoanTransaction
#     template_name = 'loans/user_transactions.html'
#     context_object_name = 'transactions'
#     paginate_by = 20

#     def get_queryset(self):
#         return LoanTransaction.objects.filter(
#             loan__user=self.request.user
#         ).order_by('-payment_date')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['total_repaid'] = self.get_queryset().filter(
#             status='approved',
#             transaction_type='repayment'
#         ).aggregate(Sum('amount'))['amount__sum'] or 0
#         return context

# class PaystackLoanPaymentView(LoginRequiredMixin, View):
#     def post(self, request, pk):
#         loan = get_object_or_404(Loan, id=pk, user=request.user)
#         amount = request.POST.get('amount')

#         try:
#             amount_in_kobo = int(float(amount) * 100)

#             # Initialize Paystack transaction
#             url = 'https://api.paystack.co/transaction/initialize'
#             headers = {
#                 'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
#                 'Content-Type': 'application/json'
#             }
#             data = {
#                 'email': request.user.email,
#                 'amount': amount_in_kobo,
#                 'callback_url': request.build_absolute_uri(reverse('loans:paystack_callback')),
#                 'reference': f"REP-{loan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
#                 'metadata': {
#                     'loan_id': loan.id,
#                     'payment_type': 'loan_repayment'
#                 }
#             }

#             response = requests.post(url, headers=headers, json=data)
#             return JsonResponse({
#                 'status': 'success',
#                 'authorization_url': response.json()['data']['authorization_url']
#             })

#         except Exception as e:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)


class PaystackLoanPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan, id=pk, user=request.user)

        try:
            data = json.loads(request.body)
            amount = data.get('amount')

            if not amount:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Amount is required'
                }, status=400)

            amount_in_kobo = int(float(amount) * 100)  # Convert to kobo

            # Initialize Paystack transaction
            url = 'https://api.paystack.co/transaction/initialize'
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            data = {
                'email': request.user.email,
                'amount': amount_in_kobo,
                'callback_url': request.build_absolute_uri(reverse('loans:paystack_callback')),
                'reference': f"REP-{loan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'metadata': {
                    'loan_id': loan.id,
                    'payment_type': 'loan_repayment'
                }
            }

            response = requests.post(url, headers=headers, json=data)
            paystack_response = response.json()

            if not response.ok:
                return JsonResponse({
                    'status': 'error',
                    'message': paystack_response.get('message', 'Payment initialization failed')
                }, status=400)

            return JsonResponse({
                'status': 'success',
                'authorization_url': paystack_response['data']['authorization_url']
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

class PaystackOnlineLoanPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(LoanApplication, id=pk, user=request.user)

        # Fixed application fee amount
        amount = 1500  # ₦1,500 application fee

        try:
            amount_in_kobo = int(float(amount) * 100)  # Convert to kobo

            # Initialize Paystack transaction
            url = 'https://api.paystack.co/transaction/initialize'
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            data = {
                'email': request.user.email,
                'amount': amount_in_kobo,
                'callback_url': request.build_absolute_uri(reverse('loans:paystack_callback')),
                'reference': f"APP-{application.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'metadata': {
                    'application_id': application.id,
                    'payment_type': 'application_fee'
                }
            }

            response = requests.post(url, headers=headers, json=data)
            return JsonResponse({
                'status': 'success',
                'authorization_url': response.json()['data']['authorization_url']
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

class PaystackOnlineLoanCallbackView(LoginRequiredMixin, View):
    def get(self, request):
        reference = request.GET.get('reference')

        try:
            # Verify transaction
            url = f'https://api.paystack.co/transaction/verify/{reference}'
            headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
            response = requests.get(url, headers=headers)
            data = response.json()

            if data['status'] and data['data']['status'] == 'success':
                payment_type = data['data']['metadata'].get('payment_type')

                if payment_type == 'application_fee':
                    # Handle application fee payment
                    application_id = data['data']['metadata'].get('application_id')
                    application = LoanApplication.objects.get(id=application_id)

                    # Update application payment status
                    application.has_paid = True
                    application.payment_date = timezone.now()
                    application.payment_reference = reference
                    application.save()

                    messages.success(request, 'Application fee payment successful! Your application will now be reviewed.')
                    return redirect('loans:application_detail', pk=application_id)

                elif payment_type == 'loan_repayment':
                    # Handle loan repayment (existing code)
                    loan_id = reference.split('-')[1]
                    loan = Loan.objects.get(id=loan_id)

                    amount = Decimal(str(data['data']['amount'])) / Decimal('100')
                    transaction = LoanTransaction.objects.create(
                        loan=loan,
                        transaction_type='repayment',
                        amount=amount,
                        payment_method='online',
                        status='approved',
                        reference_number=reference,
                        description='Online payment via Paystack',
                        approval_date=timezone.now()
                    )

                    messages.success(request, f'Payment of ₦{amount:,.2f} successful!')
                    return redirect('loans:loan_detail', pk=loan_id)

        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('loans:dashboard')  # Redirect to dashboard on error


# Admin Views
class AdminLoanApplicationListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    """Admin view to list all loan applications"""
    model = LoanApplication
    template_name = 'loans/admin/applications_list.html'
    context_object_name = 'applications'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        status = self.request.GET.get('status')
        if status:
            return LoanApplication.objects.filter(status=status).order_by('-application_date')
        return LoanApplication.objects.all().order_by('-application_date')

class AdminLoanApplicationDetailView(UserPassesTestMixin, LoginRequiredMixin, DetailView):
    """Admin view to review loan applications"""
    model = LoanApplication
    template_name = 'loans/admin/application_detail.html'
    context_object_name = 'application'

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        application = self.get_object()
        action = request.POST.get('action')

        if action == 'approve':
            application.status = 'approved'
            application.reviewed_by = request.user
            application.review_date = timezone.now()
            application.date_approved = timezone.now()
            application.save()

            # Create loan instance
            Loan.objects.create(
                user=application.user,
                application=application,
                loan_amount=application.loan_amount,
                interest_rate=application.tenure.interest_rate,
                tenure_months=application.tenure,
                monthly_payment=application.calculate_monthly_payment(),
                total_payable=application.loan_amount * (1 + application.tenure.interest_rate/100),
                disbursement_date=timezone.now(),
                next_payment_date=timezone.now().date() + timezone.timedelta(days=30),
                final_payment_date=timezone.now().date() + timezone.timedelta(days=30*application.tenure.months)
            )

            messages.success(request, "Loan application approved successfully!")

        elif action == 'reject':
            application.status = 'rejected'
            application.reviewed_by = request.user
            application.review_date = timezone.now()
            application.rejection_reason = request.POST.get('rejection_reason')
            application.save()
            messages.success(request, "Loan application rejected successfully!")

        return redirect('loans:admin_application_detail', pk=application.pk)



# loans/views.py

from django.http import FileResponse
from .utils import generate_receipt_pdf

class DownloadReceiptView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            application = LoanApplication.objects.get(pk=pk, user=request.user)
            if not application.has_paid:
                messages.error(request, "No payment found for this application.")
                return redirect('loans:application_detail', pk=pk)

            # Generate PDF
            pdf_buffer = generate_receipt_pdf(application)

            # Create response
            response = FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=f'receipt_{application.id}.pdf'
            )
            return response

        except LoanApplication.DoesNotExist:
            messages.error(request, "Application not found.")
            return redirect('loans:plans_list')









#############################################################


#ADMIN VIEWS

#######################################################


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 2

# Loan Views
class AdminLoanListView(AdminRequiredMixin, ListView):
    model = Loan
    template_name = 'loans/admin/admin_loan_list.html'
    context_object_name = 'loans'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related('user', 'application', 'loan_plan')

class AdminLoanDetailView(AdminRequiredMixin, DetailView):
    model = Loan
    template_name = 'loans/admin/admin_loan_detail.html'
    context_object_name = 'loan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.object.transactions.all().select_related('approved_by')
        return context

class AdminLoanUpdateView(AdminRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = 'loans/admin/loan_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
                'html': render_to_string(
                    'loans/admin/loan_detail_content.html',
                    {'loan': self.object},
                    request=self.request
                )
            })
        return response

    def get_success_url(self):
        return reverse_lazy('admin_loan_detail', kwargs={'pk': self.object.pk})

# Loan Application Views
class AdminLoanApplicationListView(AdminRequiredMixin, ListView):
    model = LoanApplication
    template_name = 'loans/admin/loan_application_list.html'
    context_object_name = 'applications'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related('user', 'loan_plan', 'tenure')

class AdminLoanApplicationDetailView(AdminRequiredMixin, DetailView):
    model = LoanApplication
    template_name = 'loans/admin/loan_application_detail.html'
    context_object_name = 'application'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['guarantors'] = self.object.guarantors.all()
        return context

class AdminLoanApplicationUpdateView(AdminRequiredMixin, UpdateView):
    model = LoanApplication
    form_class = LoanApplicationForm2
    template_name = 'loans/admin/loan_application_form.html'

    def form_valid(self, form):
        form.instance.reviewed_by = self.request.user
        response = super().form_valid(form)
        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
                'html': render_to_string(
                    'loans/admin/loan_application_detail_content.html',
                    {'application': self.object},
                    request=self.request
                )
            })
        return response

    def get_success_url(self):
        return reverse_lazy('admin_loan_application_detail', kwargs={'pk': self.object.pk})

# Loan Transaction Views
class AdminLoanTransactionListView(AdminRequiredMixin, ListView):
    model = LoanTransaction
    template_name = 'loans/admin/loan_transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related('loan', 'loan__user', 'approved_by')

class AdminLoanTransactionDetailView(AdminRequiredMixin, DetailView):
    model = LoanTransaction
    template_name = 'loans/admin/loan_transaction_detail.html'
    context_object_name = 'transaction'

class AdminLoanTransactionUpdateView(AdminRequiredMixin, UpdateView):
    model = LoanTransaction
    form_class = LoanTransactionForm
    template_name = 'loans/admin/loan_transaction_form.html'

    def form_valid(self, form):
        if form.instance.status == 'approved' and not form.instance.approved_by:
            form.instance.approved_by = self.request.user
        response = super().form_valid(form)
        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
                'html': render_to_string(
                    'loans/admin/loan_transaction_detail_content.html',
                    {'transaction': self.object},
                    request=self.request
                )
            })
        return response

    def get_success_url(self):
        return reverse_lazy('admin_loan_transaction_detail', kwargs={'pk': self.object.pk})





































# class PaystackOnlineLoanPaymentView(LoginRequiredMixin, View):
#     def post(self, request, pk):
#         loan = get_object_or_404(Loan, id=pk, user=request.user)
#         amount = request.POST.get('amount')

#         try:
#             amount_in_kobo = int(float(amount) * 100)

#             # Initialize Paystack transaction
#             url = 'https://api.paystack.co/transaction/initialize'
#             headers = {
#                 'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
#                 'Content-Type': 'application/json'
#             }
#             data = {
#                 'email': request.user.email,
#                 'amount': amount_in_kobo,
#                 'callback_url': request.build_absolute_uri(reverse('loans:paystack_callback')),
#                 'reference': f"REP-{loan.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
#                 'metadata': {
#                     'loan_id': loan.id,
#                     'payment_type': 'loan_repayment'
#                 }
#             }

#             response = requests.post(url, headers=headers, json=data)
#             return JsonResponse({
#                 'status': 'success',
#                 'authorization_url': response.json()['data']['authorization_url']
#             })

#         except Exception as e:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)

# class PaystackOnlineLoanCallbackView(LoginRequiredMixin, View):
#     def get(self, request):
#         reference = request.GET.get('reference')

#         try:
#             # Verify transaction
#             url = f'https://api.paystack.co/transaction/verify/{reference}'
#             headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
#             response = requests.get(url, headers=headers)
#             data = response.json()

#             if data['status'] and data['data']['status'] == 'success':
#                 # Extract loan_id from reference
#                 loan_id = reference.split('-')[1]
#                 loan = Loan.objects.get(id=loan_id)

#                 # Create transaction
#                 amount = Decimal(str(data['data']['amount'])) / Decimal('100')
#                 transaction = LoanTransaction.objects.create(
#                     loan=loan,
#                     transaction_type='repayment',
#                     amount=amount,
#                     payment_method='online',
#                     status='approved',
#                     reference_number=reference,
#                     description=f'Online payment via Paystack',
#                     approval_date=timezone.now()
#                 )

#                 messages.success(request, f'Payment of ₦{amount:,.2f} successful!')
#                 return redirect('loans:loan_detail', pk=loan_id)

#         except Exception as e:
#             messages.error(request, f'Error processing payment: {str(e)}')
#             return redirect('loans:loan_detail', pk=loan_id)
