from django import forms
from .models import Order


class OrderForm(forms.ModelForm):
    """Form for customer to enter their details"""

    class Meta:
        model = Order
        fields = ['customer_name', 'phone_number', 'phone_number_2', 'address', 'additional_notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'نام و نام خانوادگی خود را وارد کنید'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '09121234567',
                'dir': 'ltr'
            }),
            'phone_number_2': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '09121234567 (اختیاری)',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'آدرس کامل خود را وارد کنید'
            }),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'یادداشت‌های اضافی (اختیاری)'
            }),
        }


class TransactionForm(forms.Form):
    """Form for entering transaction ID"""
    transaction_id = forms.CharField(
        max_length=100,
        label='شماره پیگیری تراکنش',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'شماره پیگیری را وارد کنید',
            'dir': 'ltr'
        })
    )