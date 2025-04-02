from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import message
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from .forms import UserForm, UserProfileForm
from .models import User, UserProfile
from members.models import Member, MembershipApplication
from savings.models import SavingsTransaction, SavingsPlan, SavingsPlanType
from loans.models import LoanTransaction, Loan, LoanApplication
from django.template.defaultfilters import slugify
from members.forms import MemberForm
from .utils import detectUser, send_verification_email, get_member, get_admin
import json
from django.db.models import Sum
from django.utils.dateparse import parse_datetime
from django.core.exceptions import PermissionDenied
from django.db.models.functions import TruncMonth
from datetime import timedelta
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import logging
logger = logging.getLogger(__name__)


# Restrict the member from accessing the admin page
def check_role_member(user):
    if user.role == User.MEMBER:
        return True
    return False


# Restrict the admin from accessing the member page
def check_role_admin(user):
    if user.role == User.ADMIN:
        return True
    return False


def registerAdmin(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')
    elif request.method == 'POST':
        # Store the data and create the user
        form = UserForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, password=password)
            user.role = User.ADMIN
            user.save()

            # Send verification email
            mail_subject = 'Please activate your account'
            email_template = 'accounts/emails/account_verification_email.html'
            email_sent = send_verification_email(request, user, mail_subject, email_template)

            if email_sent:
                messages.success(request, 'Your account has been registered successfully! Please check your email to activate your account.')
            else:
                messages.warning(request, 'Account created but verification email could not be sent. Please contact support.')
                if settings.DEBUG:
                    messages.info(request, 'Since DEBUG=True, check the console for the verification link.')

            return redirect('login')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()
    context = {
        'form': form,
    }
    return render(request, 'accounts/registerAdmin.html', context)


def registerMember(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')
    elif request.method == 'POST':
        # Store the data and create the user
        form = UserForm(request.POST)
        m_form = MemberForm(request.POST, request.FILES)
        if form.is_valid() and m_form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, password=password)
            user.role = User.MEMBER
            user.save()

            # Create the member (UserProfile is created automatically by signal)
            # member = m_form.save(commit=False)
            # member.user = user
            # member.user_profile = UserProfile.objects.get(user=user)
            # member.member_slug = slugify(member.user.username)+'-'+str(member.user.id)
            # member.save()

            # Send verification email
            mail_subject = 'Please activate your account'
            email_template = 'accounts/emails/account_verification_email.html'
            email_sent = send_verification_email(request, user, mail_subject, email_template)

            if email_sent:
                messages.success(request, 'Your account has been registered successfully! Please check your email to activate your account.')
            else:
                messages.warning(request, 'Account created but verification email could not be sent. Please contact support.')
                if settings.DEBUG:
                    messages.info(request, 'Since DEBUG=True, check the console for the verification link.')

            return redirect('login')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()
        m_form = MemberForm()

    context = {
        'form': form,
        'm_form': m_form,
    }
    return render(request, 'accounts/registerMember.html', context)


def activate(request, uidb64, token):
    # Activate the user by setting the is_active status to True
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Congratulations! Your account is activated. You can now login.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('login')

def UserLoginView(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')

    elif request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email, password=password)

        if user is not None:
            if user.role == User.ADMIN:
                messages.error(request, 'Please use the admin login page.')
                return redirect('admin_login')

            auth.login(request, user)
            messages.success(request, 'You are now logged in.')

            # Check if they're a member with a profile
            member = get_member(request)
            if member:
                return redirect('members:memberDashboard')
            else:
                # Check if they have an application
                try:
                    application = MembershipApplication.objects.get(user=user)
                    return redirect('members:application_status')
                except MembershipApplication.DoesNotExist:
                    return redirect('members:apply_membership')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')



def LogoutView(request):

    auth.logout(request)
    messages.info(request, 'You are logged out.')
    return redirect('login')


@login_required(login_url='login')
def myAccount(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('login')

    # If user is authenticated, check their role and status
    if user.role == User.MEMBER:
        # Check if they're a member with a profile
        try:
            member = Member.objects.get(user=user)
            return redirect('members:memberDashboard')
        except Member.DoesNotExist:
            # Check if they have an application
            try:
                application = MembershipApplication.objects.get(user=user)
                return redirect('members:application_status')
            except MembershipApplication.DoesNotExist:
                return redirect('members:apply_membership')
    elif user.role == User.ADMIN:
        return redirect('adminDashboard')
    elif user.role == None and user.is_superuser:
        return redirect('/admin')

    # Fallback
    messages.error(request, 'Invalid user role')
    return redirect('login')


# def myAccount(request):
#     user = request.user
#     redirectUrl = detectUser(user)
#     # if redirectUrl =='/admin':
#     #   return redirect(redirectUrl)
#     return redirect(redirectUrl)


@login_required(login_url='login')
@user_passes_test(check_role_member)
def memberDashboard(request):
    user = request.user
    try:
        with transaction.atomic():
            # Get active savings plan types
            savings_types = SavingsPlanType.objects.filter(is_active=True)
            savings_amounts = []
            savings_data = []

            # Calculate savings by type
            for plan_type in savings_types:
                total = SavingsTransaction.objects.filter(
                    savings_plan__user=user,
                    savings_plan__plan_type=plan_type,
                    transaction_type='deposit',
                    status='approved'
                ).aggregate(total=Sum('amount'))['total'] or 0
                savings_amounts.append(float(total))
                savings_data.append({
                    'name': plan_type.display_name,
                    'amount': float(total)
                })

            # Calculate loan totals
            loans = Loan.objects.filter(user=user, status='active')
            loan_balance = sum(loan.loan_balance for loan in loans)
            loan_paid = sum(loan.total_paid for loan in loans)
            loan_remaining = sum(loan.remaining_balance for loan in loans)

            # Get monthly data
            today = timezone.now().date()
            first_day = today.replace(day=1)
            months = []
            savings_monthly = []
            loans_monthly = []

            # Get last 6 months of data
            for i in range(5, -1, -1):
                current_date = first_day - timedelta(days=1)
                first_day = current_date.replace(day=1)

                # Monthly savings
                monthly_savings = SavingsTransaction.objects.filter(
                    savings_plan__user=user,
                    transaction_type='deposit',
                    status='approved',
                    transaction_date__year=current_date.year,
                    transaction_date__month=current_date.month
                ).aggregate(total=Sum('amount'))['total'] or 0

                # Monthly loan payments
                monthly_loan = LoanTransaction.objects.filter(
                    loan__user=user,
                    transaction_type='repayment',
                    status='approved',
                    payment_date__year=current_date.year,
                    payment_date__month=current_date.month
                ).aggregate(total=Sum('amount'))['total'] or 0

                months.append(current_date.strftime('%B %Y'))
                savings_monthly.append(float(monthly_savings))
                loans_monthly.append(float(monthly_loan))

            # Reverse lists to show oldest to newest
            months.reverse()
            savings_monthly.reverse()
            loans_monthly.reverse()

            context = {
                'monthly_labels': json.dumps(months),
                'monthly_savings': json.dumps(savings_monthly),
                'monthly_loans': json.dumps(loans_monthly),
                'savings_types': json.dumps([plan_type.display_name for plan_type in savings_types]),
                'savings_amounts': json.dumps([float(amount) for amount in savings_amounts]),
                'savings_data': savings_data,
                'loan_paid': float(loan_paid),
                'loan_remaining': float(loan_remaining),
                'loan_balance': float(loan_balance),
            }

            return render(request, 'accounts/memberDashboard.html', context)
    except Exception as e:
        logger.error(f"Error in memberDashboard for user {user.username}: {str(e)}")
        messages.error(request, "An error occurred while loading your dashboard. Please try again.")
        return redirect('home')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def adminDashboard(request):
    # Get the last 6 months using timezone-aware dates
    end_date = timezone.now()
    start_date = end_date - timedelta(days=180)

    # Member statistics
    total_members = User.objects.filter(role=User.MEMBER).count()
    active_members = User.objects.filter(role=User.MEMBER, is_active=True).count()
    pending_applications = MembershipApplication.objects.filter(status='pending').count()

    # Monthly savings data for all members
    monthly_savings = (
        SavingsTransaction.objects
        .filter(
            transaction_type='deposit',
            status='approved',
            transaction_date__range=(start_date, end_date)
        )
        .annotate(month=TruncMonth('transaction_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    # Monthly loans data for all members
    monthly_loans = (
        LoanTransaction.objects
        .filter(
            transaction_type='repayment',
            status='approved',
            payment_date__range=(start_date, end_date)
        )
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    # Generate last 6 months properly
    months = []
    savings_data = []
    loans_data = []

    current_date = end_date
    for i in range(6):
        first_day = current_date.replace(day=1)
        month_name = current_date.strftime('%B')

        months.insert(0, month_name)

        # Find savings for this month
        month_savings = next(
            (item['total'] for item in monthly_savings if item['month'].strftime('%B') == month_name),
            0
        )
        savings_data.insert(0, float(month_savings or 0))

        # Find loans for this month
        month_loans = next(
            (item['total'] for item in monthly_loans if item['month'].strftime('%B') == month_name),
            0
        )
        loans_data.insert(0, float(month_loans or 0))

        # Move to previous month
        current_date = first_day - timedelta(days=1)

    # Savings distribution data
    savings_types = SavingsPlanType.objects.filter(is_active=True)
    savings_amounts = []

    for plan_type in savings_types:
        total = SavingsTransaction.objects.filter(
            savings_plan__plan_type=plan_type,
            transaction_type='deposit',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        savings_amounts.append(float(total))

    # Loan statistics
    active_loans = Loan.objects.filter(status='active')
    total_loan_amount = active_loans.aggregate(total=Sum('total_payable'))['total'] or 0
    total_paid = LoanTransaction.objects.filter(
        transaction_type='repayment',
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    loan_remaining = total_loan_amount - total_paid if total_loan_amount > 0 else 0

    # Calculate total savings
    total_savings = SavingsTransaction.objects.filter(
        transaction_type='deposit',
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Additional admin statistics
    pending_withdrawals = SavingsTransaction.objects.filter(
        transaction_type='withdrawal',
        status='pending'
    ).count()

    pending_loans = LoanApplication.objects.filter(status='pending').count()

    context = {
        # Chart data
        'monthly_labels': json.dumps(months),
        'monthly_savings': json.dumps(savings_data),
        'monthly_loans': json.dumps(loans_data),
        'savings_types': json.dumps([plan_type.name for plan_type in savings_types]),
        'savings_amounts': json.dumps([float(amount) for amount in savings_amounts]),
        'loan_paid': float(total_paid),
        'loan_remaining': float(loan_remaining),

        # Summary cards
        'total_savings': float(total_savings),
        'total_loans': float(total_loan_amount),
        'loan_balance': float(loan_remaining),

        # Member statistics
        'total_members': total_members,
        'active_members': active_members,
        'pending_applications': pending_applications,

        # Additional admin statistics
        'pending_withdrawals': pending_withdrawals,
        'pending_loans': pending_loans,

        'debug': True,
    }

    return render(request, 'accounts/adminDashboard.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def admin_profile(request):
    """
    Display and update admin's profile.
    """
    if not check_role_admin(request.user):
        messages.error(request, 'You are not authorized to view this page!')
        return redirect('myAccount')

    profile = get_object_or_404(UserProfile, user=request.user)
    admin = get_admin(request)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('admin_profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = UserProfileForm(instance=profile)

    context = {
        'profile_form': profile_form,
        'profile': profile,
        'admin': admin,
    }

    return render(request, 'accounts/admin_profile.html', context)


@login_required(login_url='login')
def member_profile(request):
    """
    Display and update member's profile.
    """
    if not check_role_member(request.user):
        messages.error(request, 'You are not authorized to view this page!')
        return redirect('myAccount')

    profile = get_object_or_404(UserProfile, user=request.user)
    member = get_member(request)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('member_profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = UserProfileForm(instance=profile)

    context = {
        'profile_form': profile_form,
        'profile': profile,
        'member': member,
    }

    return render(request, 'accounts/member_profile.html', context)


def AdminLoginView(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')

    elif request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email, password=password)

        if user is not None and user.role == User.ADMIN:
            auth.login(request, user)
            messages.success(request, 'You are now logged in.')
            return redirect('adminDashboard')
        else:
            messages.error(request, 'Invalid login credentials or insufficient permissions.')
            return redirect('admin_login')
    return render(request, 'accounts/admin_login.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email__exact=email)

            # send reset password email
            mail_subject = 'Reset Your Password'
            email_template = 'accounts/emails/reset_password_email.html'
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgot_password')
    return render(request, 'accounts/forgot_password.html')


def reset_password_validate(request, uidb64, token):
    # validate the user by decoding the token and user pk
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.info(request, 'Please reset your password')
        return redirect('reset_password')
    else:
        messages.error(request, 'This link has been expired!')
        return redirect('myAccount')


def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            pk = request.session.get('uid')
            user = User.objects.get(pk=pk)
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password do not match!')
            return redirect('reset_password')
    return render(request, 'accounts/reset_password.html')





# def registerAdmin(request):
#     if request.user.is_authenticated:
#         messages.warning(request, 'You are already logged in!')
#         return redirect('myAccount')

#     elif request.method == "POST":
#        print("precheck")
#        form = UserForm(request.POST)
#        m_form = MemberForm(request.POST)
#        if m_form.is_valid() and form.is_valid():
#         print("checkform")

#         first_name = form.cleaned_data['first_name']
#         last_name = form.cleaned_data['last_name']
#         username = form.cleaned_data['username']
#         email = form.cleaned_data['email']
#         password = form.cleaned_data['password']
#         print(first_name)
#         user = User.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, password=password)
#         user.role = User.ADMIN
#         print(user)
#         user.save()
#         member = m_form.save(commit=False)
#         member.user = user
#         member.member_slug = slugify(username) +str(user.id)
#         user_profile = UserProfile.objects.get(user=user)
#         member.user_profile = user_profile
#         #member.VCN_number = m_form.cleaned_data['VCN_number']
#         #member.state_of_practice = m_form.cleaned_data['state_of_practice']
#         #member.induction_date = m_form.cleaned_data['induction_date']
#         #specialty= m_form.cleaned_data['specialty']
#         #member.specialty.set(specialty)
#         print(member)
#         member.save()

#         #  Send verification email
#         mail_subject = 'Please activate your account'
#         email_template = 'accounts/emails/account_verification_email.html'
#         # json.dumps(user.__dict__)
#         # send_verification_email.delay(request, user, mail_subject, email_template)

#         send_verification_email(request, user, mail_subject, email_template)
#         messages.success(request, "Successfully, we've sent a verification email!")
#         return redirect('registerAdmin')

#        else:
#            print('invalid form')
#            print(m_form.errors)
#     else:
#         form = UserForm()
#         m_form = MemberForm()

#     context = {
#         'form': form,
#         'm_form': m_form
#     }

#     return render(request, 'accounts/registerAdmin.html', context)



# def UserLoginView(request):
#     if request.user.is_authenticated:
#         messages.warning(request, 'You are already logged in!')
#         return redirect('myAccount')

#     elif request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']
#         user = auth.authenticate(email=email, password=password)

#         if user is not None:
#             if user.role == User.ADMIN:
#                 messages.error(request, 'Please use the admin login page.')
#                 return redirect('admin_login')

#             auth.login(request, user)
#             messages.success(request, 'You are now logged in.')
#             return redirect('members:memberDashboard')  # Add namespace
#         else:
#             messages.error(request, 'Invalid login credentials')
#             return redirect('login')

#     return render(request, 'accounts/login.html')
