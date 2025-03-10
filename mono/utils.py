# utils/mono.py
from datetime import datetime, timedelta
from decimal import Decimal
# utils/mono.py
class MonoAPI:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.base_url = "https://api.withmono.com"
        self.headers = {
            "mono-sec-key": self.secret_key,
            "Content-Type": "application/json"
        }

    def exchange_code_for_account_id(self, code):
        """Exchange auth code for account ID"""
        endpoint = f"{self.base_url}/account/auth"
        response = requests.post(
            endpoint,
            headers=self.headers,
            json={'code': code}
        )

        if response.status_code == 200:
            return response.json().get('id')
        return None

    def get_account_info(self, account_id):
        """Get account information"""
        endpoint = f"{self.base_url}/accounts/{account_id}"
        response = requests.get(endpoint, headers=self.headers)
        return response.json()

    def get_statement(self, account_id, period='6months'):
        """Get bank statement"""
        if not account_id:
            raise ValueError("Account ID is required")

        endpoint = f"{self.base_url}/accounts/{account_id}/statement"
        response = requests.get(
            endpoint,
            headers=self.headers,
            params={'period': period}
        )
        return response.json()



class MonoStatementAPI:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.base_url = "https://api.withmono.com/accounts"
        self.headers = {
            "mono-sec-key": self.secret_key,
            "Content-Type": "application/json"
        }

    def get_statement(self, account_id, period='6months'):
        """Get bank statement for specified period"""
        endpoint = f"{self.base_url}/{account_id}/statement"
        params = {"period": period, "output": "json"}

        response = requests.get(
            endpoint,
            headers=self.headers,
            params=params
        )
        return response.json()

    def analyze_statement(self, statement_data):
        """Analyze statement data for loan eligibility"""
        transactions = statement_data.get('data', [])

        analysis = {
            'total_credits': Decimal('0.00'),
            'total_debits': Decimal('0.00'),
            'average_balance': Decimal('0.00'),
            'monthly_income': Decimal('0.00'),
            # 'salary_payments': [],
            # 'regular_expenses': [],
            # 'risk_factors': []
        }

        balances = []
        for transaction in transactions:
            amount = Decimal(str(transaction.get('amount', 0)))

            if transaction.get('type') == 'credit':
                analysis['total_credits'] += amount
                # Identify potential salary payments
                if self._is_salary_payment(transaction):
                    analysis['salary_payments'].append(transaction)
            else:
                analysis['total_debits'] += amount
                # Identify regular expenses
                if self._is_regular_expense(transaction):
                    analysis['regular_expenses'].append(transaction)

            balances.append(Decimal(str(transaction.get('balance', 0))))

        # Calculate average balance
        if balances:
            analysis['average_balance'] = sum(balances) / len(balances)

        # Estimate monthly income
        if analysis['salary_payments']:
            analysis['monthly_income'] = self._estimate_monthly_income(
                analysis['salary_payments']
            )

        return analysis

    # def _is_salary_payment(self, transaction):
    #     """Identify likely salary payments"""
    #     keywords = ['salary', 'payroll', 'wages']
    #     narration = transaction.get('narration', '').lower()

    #     return (
    #         transaction.get('type') == 'credit' and
    #         any(keyword in narration for keyword in keywords)
    #     )

    # def _is_regular_expense(self, transaction):
    #     """Identify regular expenses"""
    #     keywords = ['rent', 'utility', 'subscription']
    #     narration = transaction.get('narration', '').lower()

    #     return (
    #         transaction.get('type') == 'debit' and
    #         any(keyword in narration for keyword in keywords)
    #     )

    # def _estimate_monthly_income(self, salary_payments):
    #     """Estimate monthly income from salary payments"""
    #     if not salary_payments:
    #         return Decimal('0.00')

    #     amounts = [Decimal(str(payment.get('amount', 0)))
    #               for payment in salary_payments]
    #     return sum(amounts) / len(amounts)