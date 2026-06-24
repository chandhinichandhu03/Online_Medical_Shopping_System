from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    prescription_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    DELIVERY_CHOICES = (
        ('Standard', 'Standard Delivery (₹40, Free above ₹500)'),
        ('Express', 'Express Delivery (₹100)'),
        ('Same Day', 'Same Day Delivery (₹150)'),
    )
    
    PAYMENT_CHOICES = (
        ('UPI', 'UPI Payment'),
        ('Card', 'Credit/Debit Card'),
        ('NetBanking', 'Net Banking'),
        ('Wallet', 'Wallet Payment'),
        ('COD', 'Cash On Delivery'),
    )
    
    delivery_option = forms.ChoiceField(choices=DELIVERY_CHOICES, widget=forms.RadioSelect(attrs={'class': 'form-check-input'}), initial='Standard')
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, widget=forms.RadioSelect(attrs={'class': 'form-check-input'}), initial='COD')
    
    class Meta:
        model = Order
        fields = [
            'full_name', 'mobile_number', 'email', 'house_number', 'street_address', 
            'city', 'state', 'pincode', 'landmark', 'delivery_option', 'payment_method', 
            'prescription_image'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ashok Kumar', 'autocomplete': 'name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210', 'autocomplete': 'tel', 'type': 'tel'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ashok@example.com', 'autocomplete': 'email'}),
            'house_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apartment/House No.'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Street name, area', 'autocomplete': 'street-address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Chennai', 'autocomplete': 'address-level2'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tamil Nadu', 'autocomplete': 'address-level1'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 600001', 'autocomplete': 'postal-code', 'inputmode': 'numeric', 'pattern': '[0-9]{6}'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Near City Hospital'}),
        }
