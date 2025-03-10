from django import forms
from .models import User, UserProfile
from .validators import allow_only_images_validator


class UserForm(forms.ModelForm):
    
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self). __init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update(
            {
             'type': 'text',
             'class' : 'form-control',
             'placeholder' : 'first name' 
            }
        )
        self.fields["last_name"].widget.attrs.update(
            {
             'type': 'text',
             'class' : 'form-control',
             'placeholder' : 'last name' 
            }
        )
        self.fields["email"].widget.attrs.update(
            {
             'type': 'email',
             'class' : 'form-control',
             'placeholder' : 'email' 
            }
        )
        self.fields["username"].widget.attrs.update(
            {
             'type': 'text',
             'class' : 'form-control',
             'placeholder' : 'username' 
            }
        )
        self.fields["password"].widget.attrs.update(
            {
             'type': 'password',
             'class' : 'form-control',
             'placeholder' : 'password' 
            }
        )
        self.fields["confirm_password"].widget.attrs.update(
             {
              'type': 'password',
              'class' : 'form-control',
              'placeholder' : 'confirm password' 
             }
         )
    
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match!"
            )



class UserProfileForm(forms.ModelForm):
    address = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your address'
        })
    )
    phone_number = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    profile_picture = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        validators=[allow_only_images_validator],
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'phone_number', 'address', 'country', 'state', 'city']

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        
        # Common attributes for text fields
        text_field_attrs = {
            'class': 'form-control'
        }
        
        # Update widget attributes for each field
        self.fields['country'].widget = forms.TextInput(attrs={
            **text_field_attrs,
            'placeholder': 'Enter your country'
        })
        self.fields['state'].widget = forms.TextInput(attrs={
            **text_field_attrs,
            'placeholder': 'Enter your state'
        })
        self.fields['city'].widget = forms.TextInput(attrs={
            **text_field_attrs,
            'placeholder': 'Enter your city'
        })

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        if len(phone_number) != 11:
            raise forms.ValidationError("Phone number must be 11 digits long.")
        
        return phone_number