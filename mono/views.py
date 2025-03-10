from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
import requests
import json
import time

from .utils import MonoStatementAPI
from .models import BankStatement, MonoAccount


class MonoConnectView(LoginRequiredMixin, View):
    template_name = 'mono/mono_connect.html'

    def get(self, request):
        # Generate a unique reference for this connection attempt
        timestamp = int(time.time())

        context = {
            'mono_public_key': settings.MONO_PUBLIC_KEY,
            'reference': f"{request.user.id}_{slugify(request.user.email)}_{timestamp}"
        }
        return render(request, self.template_name, context)

class MonoAuthView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            # Parse and validate request data
            try:
                data = json.loads(request.body)
                code = data.get('code')
                if not code:
                    return JsonResponse({
                        'success': False,
                        'error': 'Authorization code is required'
                    }, status=400)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid request data'
                }, status=400)

            # Exchange code for account ID
            try:
                response = requests.post(
                    'https://api.withmono.com/account/auth',
                    headers={
                        'Content-Type': 'application/json',
                        'mono-sec-key': settings.MONO_SECRET_KEY
                    },
                    json={'code': code},
                    timeout=30
                )
                print("Mono API Response Status:", response.status_code)

                response_data = response.json()
                print("Mono API Response:", json.dumps(response_data, indent=2))

                if response.status_code != 200:
                    error_msg = response_data.get('message', 'Failed to authenticate with Mono')
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=400)

            except requests.RequestException as e:
                print("Network error:", str(e))
                return JsonResponse({
                    'success': False,
                    'error': f'Network error: {str(e)}'
                }, status=400)

            # Extract account ID from response
            account_id = None
            if isinstance(response_data, dict):
                # Try different possible response structures
                if 'id' in response_data:
                    account_id = response_data['id']
                elif 'account' in response_data and isinstance(response_data['account'], dict):
                    account_id = response_data['account'].get('id')
                elif 'data' in response_data and isinstance(response_data['data'], dict):
                    account_id = response_data['data'].get('id')

            if not account_id:
                print("Failed to extract account ID from response:", response_data)
                return JsonResponse({
                    'success': False,
                    'error': 'Could not retrieve account ID from Mono'
                }, status=400)

            # Create or update MonoAccount
            try:
                # Delete any existing account for this user first
                MonoAccount.objects.filter(user=request.user).delete()

                # Create new account
                mono_account = MonoAccount.objects.create(
                    user=request.user,
                    account_id=account_id
                )
                print("Created new MonoAccount with ID:", account_id)

                return JsonResponse({
                    'success': True,
                    'message': 'Successfully linked bank account',
                    'redirect_url': reverse('mono:mono_connect')
                })

            except Exception as e:
                print(f"Database error while saving MonoAccount: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to save account information'
                }, status=400)

        except Exception as e:
            print("Unexpected error:", str(e))
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)



# class MonoAuthView(LoginRequiredMixin, View):
#     def post(self, request):
#         try:
#             data = json.loads(request.body)
#             code = data.get('code')

#             # Exchange code for account ID
#             response = requests.post(
#                 'https://api.withmono.com/v2/accounts/auth',
#                 headers={
#                     'Content-Type': 'application/json',
#                     'mono-sec-key': settings.MONO_SECRET_KEY
#                 },
#                 json={'code': code}
#             )

#             if response.status_code == 200:
#                 account_data = response.json()
#                 account_id = account_data.get('id')

#                 # Create or update MonoAccount
#                 mono_account, created = MonoAccount.objects.update_or_create(
#                     user=request.user,
#                     defaults={'account_id': account_id}
#                 )

#                 return JsonResponse({
#                     'success': True,
#                     'redirect_url': reverse('mono:bank_statement')
#                 })

#             return JsonResponse({
#                 'success': False,
#                 'error': 'Failed to authenticate with Mono'
#             }, status=400)

#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             }, status=400)


# class BankStatementView(LoginRequiredMixin, View):
#     template_name = 'mono/bank_statement.html'

#     def get(self, request):
#         try:
#             mono_account = get_object_or_404(MonoAccount, user=request.user)
#             mono_api = MonoStatementAPI(settings.MONO_SECRET_KEY)

#             # Get statement data
#             statement_data = mono_api.get_statement(mono_account.account_id, period='6months')

#             # Analyze statement
#             analysis = mono_api.analyze_statement(statement_data)

#             # Save statement and analysis
#             bank_statement, created = BankStatement.objects.update_or_create(
#                 user=request.user,
#                 mono_account=mono_account,
#                 defaults={
#                     'period': '6months',
#                     'statement_data': statement_data,
#                     'average_balance': analysis['average_balance'],
#                     'total_credits': analysis['total_credits'],
#                     'total_debits': analysis['total_debits'],
#                     'analysis_complete': True
#                 }
#             )

#             context = {
#                 'statement': bank_statement,
#                 'analysis': analysis,
#                 'salary_payments': analysis.get('salary_payments', []),
#                 'regular_expenses': analysis.get('regular_expenses', [])
#             }

#             return render(request, self.template_name, context)

#         except MonoAccount.DoesNotExist:
#             return redirect('mono:mono_connect')
