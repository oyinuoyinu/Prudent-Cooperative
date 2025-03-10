from .models import User
from members.models import Member
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.conf import settings

def detectUser(user):
    if user.role == User.MEMBER:
        # Check if they're a member with a profile
        try:
            member = Member.objects.get(user=user)
            redirectUrl = 'members:memberDashboard'
        except Member.DoesNotExist:
            # Check if they have an approved application
            try:
                application = MembershipApplication.objects.get(user=user)
                if application.status == 'APPROVED':
                    # Let memberDashboard handle member creation
                    redirectUrl = 'members:memberDashboard'
                else:
                    redirectUrl = 'members:application_status'
            except MembershipApplication.DoesNotExist:
                redirectUrl = 'members:apply_membership'
        return redirectUrl
    elif user.role == User.ADMIN:
        redirectUrl = 'adminDashboard'
        return redirectUrl
    elif user.role == None and user.is_superuser:
        redirectUrl = '/admin'
        return redirectUrl

# def detectUser(user):
#     if user.role == User.MEMBER:
#         redirectUrl = 'members:memberDashboard'
#         return redirectUrl
#     elif user.role == User.ADMIN:
#         redirectUrl = 'adminDashboard'
#         return redirectUrl
#     elif user.role == None and user.is_superuser:
#         redirectUrl = '/admin'
#         return redirectUrl


def send_verification_email(request, user, mail_subject, email_template):
    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        current_site = get_current_site(request)
        message = render_to_string(email_template, {
            'user': user,
            'domain': current_site,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        })
        to_email = user.email
        mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
        mail.content_subtype = "html"
        mail.send()
        return True
    except Exception as e:
        print(f'Error sending verification email to {user.email}: {str(e)}')
        return False


def send_notification(mail_subject, mail_template, context):
    from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(mail_template, context)
    if(isinstance(context['to_email'], str)):
        to_email = []
        to_email.append(context['to_email'])
    else:
        to_email = context['to_email']
    mail = EmailMessage(mail_subject, message, from_email, to=to_email)
    mail.content_subtype = "html"
    mail.send()


def send_appointment_email(mail_subject, mail_template, context):

        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = context['to_email']
        message = render_to_string(mail_template, context)
        mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
        mail.content_subtype = "html"
        mail.send()


def get_member(request):
    try:
        member = Member.objects.get(user=request.user)
        return member
    except Member.DoesNotExist:
        return None

def get_admin(request):
    try:
        admin = User.objects.get(user=request.user, role=User.ADMIN)
    except:
        admin = None
    return admin