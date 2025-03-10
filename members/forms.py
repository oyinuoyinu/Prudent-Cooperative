from django import forms
from django.core.validators import RegexValidator
from .models import Member, MembershipApplication
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Div, HTML, Submit

phone_validator = RegexValidator(
    regex=r'^\+?234?\d{10,11}$',
    message="Phone number must be entered in the format: '+2341234567890'."
)

class MembershipApplicationForm(forms.ModelForm):
    phone_number = forms.CharField(validators=[phone_validator])
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Must be at least 18 years old'
    )
    profile_picture = forms.ImageField(
        help_text='Upload a clear photo for your membership card'
    )
    account_number = forms.CharField(
        max_length=10,
        min_length=10,
        help_text="Enter your 10-digit account number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'pattern': '[0-9]{10}'}),
    )

    class Meta:
        model = MembershipApplication
        fields = [
            'full_name', 'date_of_birth', 'state_of_origin', 'state_of_residence',
            'profession', 'phone_number', 'email', 'profile_picture', 'savings_type',
            'bank_name', 'account_name', 'account_number',
            'next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_phone',
            'how_did_you_hear', 'referrer_name', 'referrer_is_member'
        ]
        widgets = {
            'how_did_you_hear': forms.Textarea(attrs={'rows': 3}),
            'savings_type': forms.Select(attrs={'class': 'form-select'}),
            'bank_name': forms.Select(attrs={'class': 'form-select'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'state_of_origin': forms.TextInput(attrs={'class': 'form-control'}),
            'state_of_residence': forms.TextInput(attrs={'class': 'form-control'}),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_name': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'referrer_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number')
        if not account_number.isdigit():
            raise forms.ValidationError("Account number must contain only digits")
        if len(account_number) != 10:
            raise forms.ValidationError("Account number must be exactly 10 digits")
        return account_number

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'

        # Make bank fields required for new applications
        self.fields['bank_name'].required = True
        self.fields['account_name'].required = True
        self.fields['account_number'].required = True

        self.helper.layout = Layout(
            HTML("<h5 class='mb-4'>Basic Information</h5>"),
            Row(
                Column('full_name', css_class='form-group col-md-6 mb-3'),
                Column('date_of_birth', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('state_of_origin', css_class='form-group col-md-6 mb-3'),
                Column('state_of_residence', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('profession', css_class='form-group col-md-6 mb-3'),
                Column('phone_number', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('profile_picture', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            HTML("<h5 class='mb-4 mt-4'>Savings Information</h5>"),
            Row(
                Column('savings_type', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            HTML("<h5 class='mb-4 mt-4'>Bank Information</h5>"),
            Row(
                Column('bank_name', css_class='form-group col-md-6 mb-3'),
                Column('account_name', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('account_number', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            HTML("<h5 class='mb-4 mt-4'>Next of Kin Information</h5>"),
            Row(
                Column('next_of_kin_name', css_class='form-group col-md-6 mb-3'),
                Column('next_of_kin_relationship', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('next_of_kin_phone', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            HTML("<h5 class='mb-4 mt-4'>Referral Information</h5>"),
            Row(
                Column('how_did_you_hear', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('referrer_name', css_class='form-group col-md-6 mb-3'),
                Column('referrer_is_member', css_class='form-group col-md-6 mb-3 mt-4'),
                css_class='form-row'
            ),
            Submit('submit', 'Submit Application', css_class='btn btn-primary mt-4')
        )

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['is_active', 'blacklisted', 'blacklist_reason']
        widgets = {
            'blacklist_reason': forms.Textarea(attrs={'rows': 3}),
        }

class MembershipApplicationForm(forms.ModelForm):
    # Fields from MembershipApplication
    full_name = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    state_of_residence = forms.CharField(max_length=50, required=False)
    profile_picture = forms.ImageField(required=False)
    profession = forms.CharField(max_length=100, required=False)

    class Meta:
        model = MembershipApplication
        fields = '__all__'  # Include all fields from MembershipApplication

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('full_name', css_class='col-md-6'),
                Column('phone_number', css_class='col-md-6'),
                css_class='mb-3'
            ),
            Row(
                Column('state_of_residence', css_class='col-md-6'),
                Column('profession', css_class='col-md-6'),
                css_class='mb-3'
            ),
            Row(
                Column('profile_picture', css_class='col-12'),
                css_class='mb-3'
            )
        )

        # Pre-populate fields from MembershipApplication if available
        if self.instance and hasattr(self.instance, 'application'):
            app = self.instance.application
            self.fields['full_name'].initial = app.full_name
            self.fields['phone_number'].initial = app.phone_number
            self.fields['state_of_residence'].initial = app.state_of_residence
            self.fields['profession'].initial = app.profession

    def save(self, commit=True):
        member = super().save(commit=False)

        if member.application:
            member.application.full_name = self.cleaned_data['full_name']
            member.application.phone_number = self.cleaned_data['phone_number']
            member.application.state_of_residence = self.cleaned_data['state_of_residence']
            member.application.profession = self.cleaned_data['profession']

            if self.cleaned_data.get('profile_picture'):
                member.application.profile_picture = self.cleaned_data['profile_picture']

            if commit:
                member.application.save()
                member.save()

        return member





class AdminMemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['is_active', 'blacklisted', 'blacklist_reason']
        widgets = {
            'blacklist_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'blacklisted': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('is_active', css_class='form-group col-md-6 mb-3'),
                Column('blacklisted', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('blacklist_reason', css_class='form-group col-12 mb-3'),
                css_class='form-row'
            )
        )

class AdminMembershipApplicationForm(forms.ModelForm):
    class Meta:
        model = MembershipApplication
        fields = [
            'status', 'admin_notes', 'rejection_reason',
            'payment_completed', 'payment_reference'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'rejection_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'payment_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-6 mb-3'),
                Column('payment_completed', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('payment_reference', css_class='form-group col-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('admin_notes', css_class='form-group col-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('rejection_reason', css_class='form-group col-12 mb-3'),
                css_class='form-row'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')

        if status == 'REJECTED' and not rejection_reason:
            raise forms.ValidationError({
                'rejection_reason': 'Rejection reason is required when status is Rejected'
            })

        return cleaned_data