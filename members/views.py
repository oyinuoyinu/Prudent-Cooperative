from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView, CreateView
from django.urls import reverse_lazy
from .models import Member, MembershipApplication, PaymentVerification
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_member, check_role_admin, memberDashboard
from accounts.utils import detectUser, get_member
from django.shortcuts import render, HttpResponse
import json
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views.generic import ListView
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
import requests
from .forms import MembershipApplicationForm, MemberForm
from django.views.decorators.csrf import csrf_exempt
import logging
import time
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from .forms import MembershipApplicationForm, AdminMemberForm, AdminMembershipApplicationForm
logger = logging.getLogger(__name__)

@login_required(login_url='login')
@user_passes_test(check_role_member)
def profile(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Member profile not found.')
        return redirect('members:apply_membership')

    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('members:profile')
    else:
        form = MemberForm(instance=member)

    # Get application and payment history
    application = member.application
    payments = PaymentVerification.objects.filter(application=application)

    context = {
        'form': form,
        'member': member,
        'application': application,
        'payments': payments,
    }
    return render(request, 'members/profile.html', context)


# class MembershipApplicationView(LoginRequiredMixin, DetailView):
#     model = MembershipApplication
#     form_class = MemberProfileForm
#     template_name = 'members/member_profile.html'
#     success_url = reverse_lazy('members:profile')

#     def get_object(self, queryset=None):
#         return Member.objects.get(user=self.request.user)

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['member'] = self.get_object()
#         return context

#     def form_valid(self, form):
#         messages.success(self.request, 'Your profile has been updated successfully!')
#         return super().form_valid(form)

class MemberProfileView(LoginRequiredMixin, DetailView):
    model = MembershipApplication
    template_name = 'members/member_profile.html'
    context_object_name = 'application'

    def get_object(self, queryset=None):
        return get_object_or_404(MembershipApplication, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = MembershipApplicationForm(instance=self.get_object())
        return context

@login_required
def apply_membership(request):
    # Check if user already has an application
    try:
        application = MembershipApplication.objects.get(user=request.user)
        if application.payment_completed:
            return redirect('members:memberDashboard')
        return redirect('members:payment_initiate')
    except MembershipApplication.DoesNotExist:
        pass

    if request.method == 'POST':
        form = MembershipApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                application = form.save(commit=False)
                application.user = request.user
                application.save()
                messages.success(request, 'Application submitted successfully. Please proceed with payment.')
                return redirect('members:payment_initiate')
            except Exception as e:
                messages.error(request, 'Error saving application. Please try again.')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = MembershipApplicationForm(initial={
            'email': request.user.email,
            'full_name': f"{request.user.first_name} {request.user.last_name}"
        })

    return render(request, 'members/apply.html', {'form': form})


@login_required
def member_profile(request):
    try:
        member = Member.objects.get(user=request.user)
        return render(request, 'members/profile.html', {'member': member})
    except Member.DoesNotExist:
        return redirect('members:apply_membership')


@login_required(login_url='login')
@user_passes_test(check_role_member)
def application_status(request):
    try:
        application = MembershipApplication.objects.get(user=request.user)
        payments = PaymentVerification.objects.filter(application=application)

        # If application is approved but no member profile exists
        if application.status == 'APPROVED':
            try:
                member = Member.objects.get(user=request.user)
                return redirect('members:memberDashboard')
            except Member.DoesNotExist:
                return redirect('members:memberDashboard')  # pass Continue showing application status

        return render(request, 'members/application_status.html', {
            'application': application,
            'payments': payments
        })
    except MembershipApplication.DoesNotExist:
        messages.error(request, 'No application found.')
        return redirect('members:apply_membership')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def review_applications(request):
    applications = MembershipApplication.objects.filter(status='PENDING').order_by('-application_date')
    return render(request, 'members/review_applications.html', {
        'applications': applications
    })


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def review_application(request, application_id):
    application = get_object_or_404(MembershipApplication, id=application_id)
    payments = PaymentVerification.objects.filter(application=application)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            # Verify all pending payments first
            if application.registration_payment_proof:
                PaymentVerification.objects.get_or_create(
                    application=application,
                    payment_type='REGISTRATION',
                    defaults={
                        'amount': 1000,  # Registration fee amount
                        'payment_proof': application.registration_payment_proof,
                        'verified': True,
                        'verified_by': request.user,
                        'verification_date': timezone.now(),
                        'verification_notes': 'Verified during application approval'
                    }
                )
                application.registration_fee_paid = True

            if application.welfare_payment_proof:
                PaymentVerification.objects.get_or_create(
                    application=application,
                    payment_type='WELFARE',
                    defaults={
                        'amount': 1000,  # Welfare fee amount
                        'payment_proof': application.welfare_payment_proof,
                        'verified': True,
                        'verified_by': request.user,
                        'verification_date': timezone.now(),
                        'verification_notes': 'Verified during application approval'
                    }
                )
                application.welfare_fee_paid = True

            # Update application status
            application.status = 'APPROVED'
            application.approval_date = timezone.now()
            application.save()

            # The Member object will be created by the signal handler
            # No need to create it here

            messages.success(request, 'Application approved, payments verified, and member profile created.')
        elif action == 'reject':
            application.status = 'REJECTED'
            application.rejection_reason = request.POST.get('rejection_reason', '')
            application.save()
            messages.success(request, 'Application rejected.')

        return redirect('members:review_applications')

    return render(request, 'members/review_application.html', {
        'application': application,
        'payments': payments
    })


class PaystackMembershipPaymentView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            application = get_object_or_404(MembershipApplication, user=request.user)

            if application.payment_completed:
                messages.info(request, 'Payment has already been completed.')
                return redirect('members:memberDashboard')

            context = {
                'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
                'email': request.user.email,
                'amount': settings.MEMBERSHIP_FEE,
                'application': application
            }
            return render(request, 'members/payment_initiate.html', context)
        except MembershipApplication.DoesNotExist:
            messages.error(request, 'Please submit your membership application first.')
            return redirect('members:apply_membership')

    def post(self, request):
        try:
            application = get_object_or_404(MembershipApplication, user=request.user)

            if application.payment_completed:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment has already been completed'
                }, status=400)

            # Convert amount to kobo
            amount_in_kobo = int(settings.MEMBERSHIP_FEE * 100)

            # Generate unique reference
            reference = f"MEM-{application.application_number}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

            # Initialize Paystack transaction
            url = 'https://api.paystack.co/transaction/initialize'
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }

            data = {
                'email': request.user.email,
                'amount': amount_in_kobo,
                'callback_url': request.build_absolute_uri(reverse('members:payment_callback')),
                'reference': reference,
                'metadata': {
                    'application_id': str(application.id),
                    'user_id': request.user.id,
                    'application_number': application.application_number
                }
            }

            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()

            if response_data['status']:
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': response_data['data']['authorization_url'],
                    'reference': reference,
                    'metadata': {
                        'application_id': application.id,
                        'user_id': request.user.id,
                        'application_number': application.application_number
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not initialize payment'
                }, status=400)

        except Exception as e:
            logger.error(f"Error in PaystackMembershipPaymentView: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)


class PaystackCallbackView(LoginRequiredMixin, View):
    def get(self, request):
        reference = request.GET.get('reference')
        logger.info(f"Received Paystack callback for membership payment: {reference}")

        try:
            # Verify transaction
            url = f'https://api.paystack.co/transaction/verify/{reference}'
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
            }

            response = requests.get(url, headers=headers)
            response_data = response.json()

            logger.info(f"Paystack verification response: {response_data}")

            if response_data['status'] and response_data['data']['status'] == 'success':
                # Get application from metadata
                application_id = response_data['data']['metadata']['application_id']
                application = MembershipApplication.objects.get(id=application_id)

                # Update application status
                application.payment_completed = True
                application.payment_reference = reference
                application.payment_date = timezone.now()
                application.status = 'PENDING'
                application.approval_date = timezone.now()
                application.save()

                # Create member profile
                Member.objects.create(
                    user=application.user,
                    application=application
                )

                messages.success(request, 'Payment successful! Your membership has been approved.')
                return redirect('members:memberDashboard')

            else:
                logger.error(f"Payment verification failed. Status: {response_data.get('data', {}).get('status')}")
                messages.error(request, 'Payment verification failed. Please try again or contact support.')
                return redirect('members:payment_initiate')

        except Exception as e:
            logger.error(f"Error in PaystackCallbackView: {str(e)}")
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('members:payment_initiate')





########################
#Admin VIEWS
################



class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# Member Views
class AdminMemberListView(AdminRequiredMixin, ListView):
    model = Member
    template_name = 'members/admin/member_list.html'
    context_object_name = 'members'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')

        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True, blacklisted=False)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status == 'blacklisted':
                queryset = queryset.filter(blacklisted=True)

        if search:
            queryset = queryset.filter(
                models.Q(membership_number__icontains=search) |
                models.Q(user__first_name__icontains=search) |
                models.Q(user__last_name__icontains=search) |
                models.Q(user__email__icontains=search)
            )

        return queryset.select_related('user', 'application')

class AdminMemberDetailView(AdminRequiredMixin, DetailView):
    model = Member
    template_name = 'members/admin/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdminMemberForm(instance=self.object)
        return context

class AdminMemberUpdateView(AdminRequiredMixin, UpdateView):
    model = Member
    form_class = AdminMemberForm
    template_name = 'members/admin/member_form.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
                'html': render_to_string(
                    'members/admin/member_detail_content.html',
                    {'member': self.object},
                    request=self.request
                )
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JsonResponse({
                'success': False,
                'html': render_to_string(
                    'members/admin/member_form.html',
                    {'form': form},
                    request=self.request
                )
            })
        return super().form_invalid(form)

class AdminMemberDeleteView(AdminRequiredMixin, DeleteView):
    model = Member
    template_name = 'members/admin/member_confirm_delete.html'
    success_url = reverse_lazy('members:admin_member_list')

    def delete(self, request, *args, **kwargs):
        if request.is_ajax():
            self.object = self.get_object()
            self.object.delete()
            return JsonResponse({'success': True})
        return super().delete(request, *args, **kwargs)

# MembershipApplication Views
class AdminMembershipApplicationListView(AdminRequiredMixin, ListView):
    model = MembershipApplication
    template_name = 'members/admin/application_list.html'
    context_object_name = 'applications'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status.upper())

        if search:
            queryset = queryset.filter(
                models.Q(application_number__icontains=search) |
                models.Q(full_name__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(phone_number__icontains=search)
            )

        return queryset.select_related('user')

class AdminMembershipApplicationDetailView(AdminRequiredMixin, DetailView):
    model = MembershipApplication
    template_name = 'members/admin/application_detail.html'
    context_object_name = 'application'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdminMembershipApplicationForm(instance=self.object)
        return context

class AdminMembershipApplicationUpdateView(AdminRequiredMixin, UpdateView):
    model = MembershipApplication
    form_class = AdminMembershipApplicationForm
    template_name = 'members/admin/application_form.html'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
                'html': render_to_string(
                    'members/admin/application_detail_content.html',
                    {'application': self.object},
                    request=self.request
                )
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JsonResponse({
                'success': False,
                'html': render_to_string(
                    'members/admin/application_form.html',
                    {'form': form},
                    request=self.request
                )
            })
        return super().form_invalid(form)

class AdminMembershipApplicationDeleteView(AdminRequiredMixin, DeleteView):
    model = MembershipApplication
    template_name = 'members/admin/application_confirm_delete.html'
    success_url = reverse_lazy('members:admin_application_list')

    def delete(self, request, *args, **kwargs):
        if request.is_ajax():
            self.object = self.get_object()
            self.object.delete()
            return JsonResponse({'success': True})
        return super().delete(request, *args, **kwargs)