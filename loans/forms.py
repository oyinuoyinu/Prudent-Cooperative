from django import forms
from .models import LoanApplication, Guarantor, LoanTransaction, Loan, LoanPlanType
from django.forms import inlineformset_factory, formset_factory

class GuarantorForm(forms.ModelForm):
    class Meta:
        model = Guarantor
        fields = [
            'full_name',
            'email',
            'phone_number',
            'relationship',
            'occupation',
            'address',
            'id_card',
            'guarantee_letter',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relationship'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'id_card': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'guarantee_letter': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }

class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = [
            'loan_amount',
            'purpose',
            'plan_type',
        ]
        widgets = {
            'loan_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter loan amount',
                'min': '0',
                'step': '0.01'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain the purpose of the loan'
            }),
            'plan_type': forms.Select(attrs={
                'class': 'form-control'
            }),

        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.fields['plan_type'].queryset = LoanPlanType.objects.filter(is_active=True)
        super().__init__(*args, **kwargs)

    def clean_loan_amount(self):
        amount = self.cleaned_data['loan_amount']
        if not self.cleaned_data['plan_type']:
            raise forms.ValidationError("Loan plan is required")

        if amount < self.cleaned_data['plan_type'].min_amount:
            raise forms.ValidationError(f"Amount cannot be less than ₦{self.cleaned_data['plan_type'].min_amount:,.2f}")

        if amount > self.cleaned_data['plan_type'].max_amount:
            raise forms.ValidationError(f"Amount cannot exceed ₦{self.cleaned_data['plan_type'].max_amount:,.2f}")

        return amount



GuarantorFormSet = formset_factory(
    GuarantorForm,
    extra=2,
    min_num=1,
    validate_min=True,
)

class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanTransaction
        fields = [
            'amount',
            'payment_proof',
            'description'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payment amount',
                'min': '1000',
                'step': '0.01'
            }),
            'payment_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add any additional notes about this payment'
            })
        }

    def __init__(self, *args, **kwargs):
        # Pop loan from kwargs before calling parent's __init__
        self.loan = kwargs.pop('loan', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise forms.ValidationError('Please enter a payment amount.')

        if amount < 1000:
            raise forms.ValidationError('Minimum payment amount is ₦1,000.')

        if self.loan and amount > self.loan.loan_balance:
            raise forms.ValidationError(f'Payment amount cannot exceed the loan balance of ₦{self.loan.loan_balance:,.2f}.')

        return amount





class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            'loan_plan', 'loan_amount', 'monthly_payment',
            'total_payable', 'status', 'payment_status',
            'next_payment_date', 'final_payment_date'
        ]
        widgets = {
            'next_payment_date': forms.DateInput(attrs={'type': 'date'}),
            'final_payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LoanApplicationForm2(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = [
            'plan_type', 'loan_amount',
            'purpose', 'status', 'review_notes'
        ]
        widgets = {
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'loan_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'review_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'status': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan_type'].queryset = LoanPlanType.objects.filter(is_active=True)

class LoanTransactionForm(forms.ModelForm):
    class Meta:
        model = LoanTransaction
        fields = [
            'transaction_type', 'amount', 'payment_method',
            'payment_proof', 'reference_number', 'description',
            'status'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }