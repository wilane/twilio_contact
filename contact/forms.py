from django import forms
from contact.models import contact

from django.contrib.localflavor.us.forms import USPhoneNumberField

class ContactForm(forms.ModelForm):    
    class Meta:
        model = contact
