from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    prescription_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Order
        fields = ['address', 'prescription_image']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
