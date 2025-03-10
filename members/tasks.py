# from celery import shared_task
# from django.core.mail import EmailMessage, message
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.shortcuts import redirect
# from django.contrib import messages



# @shared_task
# def send_zoom_invitation(mail_subject, mail_template, context):
#     try:
#         from_email = settings.DEFAULT_FROM_EMAIL
#         to_email = context['to_email']
#         message = render_to_string(mail_template, context)
#         mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
#         mail.content_subtype = "html"
#         mail.send()

#     except Exception as e:
#        # If there is an error, notify the user with a flash message
#         messages.error('An error occurred while sending the email')
#         return redirect('meeting_info')

# @shared_task
# def send_zoom_notification(mail_subject, mail_template, context):
#     try:
#         from_email = settings.DEFAULT_FROM_EMAIL
#         to_email = context['to_email']
#         message = render_to_string(mail_template, context)
#         mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
#         mail.content_subtype = "html"
#         mail.send()

#     except Exception as e:
#         # If there is an error, notify the user with a flash message
#         messages.error('An error occurred while sending the email')
#         return redirect('meeting_info')