from django import forms
from .models import PaymentAccount, SavingsPlan, SavingsTransaction, SavingsPlanType

class PaymentAccountForm(forms.ModelForm):
    class Meta:
        model = PaymentAccount
        fields = ['plan_type', 'account_name', 'account_number', 'bank_name']
        widgets = {
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active plan types
        self.fields['plan_type'].queryset = SavingsPlanType.objects.filter(is_active=True)

class SavingsPlanForm(forms.ModelForm):
    class Meta:
        model = SavingsPlan
        fields = ['plan_type', 'status', 'interest_rate', 'maturity_date']
        widgets = {
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'maturity_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active plan types that have payment accounts
        self.fields['plan_type'].queryset = SavingsPlanType.objects.filter(
            is_active=True,
            payment_accounts__isnull=False
        ).distinct()

        # Add help text
        self.fields['plan_type'].help_text = "Select a savings plan type. Each plan type has different interest rates and minimum balance requirements."

class SavingsTransactionForm(forms.ModelForm):
    class Meta:
        model = SavingsTransaction
        fields = ['status', 'description']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CreateSavingsPlanForm(forms.ModelForm):
    class Meta:
        model = SavingsPlan
        fields = ['plan_type', 'amount']
        labels = {
            'plan_type': 'Plan Type',
            'amount': 'Initial Amount'
        }
        widgets = {
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'})
        }


class CreateDepositForm(forms.ModelForm):

    # Read-only fields for payment account information
    bank_name = forms.CharField(disabled=True, required=False)
    account_name = forms.CharField(disabled=True, required=False)
    account_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f8f9fa; cursor: text;'
        })
    )


    class Meta:
        model = SavingsTransaction
        fields = [
            'amount', 'payment_proof'
            ]
        labels = {
            'amount': 'Deposit Amount',
            'payment_proof': 'Payment Proof'
        }
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_proof': forms.FileInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        savings_plan = kwargs.pop('savings_plan', None)
        super().__init__(*args, **kwargs)

        if savings_plan and savings_plan.payment_account:
            # Set initial values for read-only fields
            self.fields['bank_name'].initial = savings_plan.payment_account.bank_name
            self.fields['account_name'].initial = savings_plan.payment_account.account_name
            self.fields['account_number'].initial = savings_plan.payment_account.account_number

            # Add help text for payment proof
            self.fields['payment_proof'].help_text = f"Please upload proof of payment to {savings_plan.payment_account.bank_name} - {savings_plan.payment_account.account_number}"
            # Add help text for account number
            self.fields['account_number'].help_text = "Click to select and copy the account number"



class CreateWithdrawalForm(forms.ModelForm):
    class Meta:
        model = SavingsTransaction
        fields = ['amount', 'description']
        labels = {
            'amount': 'Withdrawal Amount',
            'description': 'Description'
        }
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'})
        }
    def __init__(self, *args, **kwargs):
        self.savings_plan = kwargs.pop('savings_plan', None)
        super().__init__(*args, **kwargs)
        if self.savings_plan:
            self.fields['amount'].help_text = (
                f"Available balance: ₦{self.savings_plan.amount:,.2f}<br>"
                f"Minimum balance required: ₦{self.savings_plan.plan_type.minimum_balance:,.2f}"
            )

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not self.savings_plan:
            raise ValidationError("No savings plan specified")

        if amount <= 0:
            raise ValidationError("Amount must be greater than zero")

        if amount > self.savings_plan.amount:
            raise ValidationError("Withdrawal amount exceeds available balance")

        remaining_balance = self.savings_plan.amount - amount
        if remaining_balance < self.savings_plan.plan_type.minimum_balance:
            raise ValidationError(
                f"Withdrawal would put balance below minimum required balance of "
                f"₦{self.savings_plan.plan_type.minimum_balance:,.2f}"
            )

        return amount