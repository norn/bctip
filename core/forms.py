# -*- coding: utf-8 -*-
from django import forms
from core.models import *
import re
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l
from django.conf import settings

CURRENCIES = (('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'))
TARGET_LANGUAGES = settings.LANGUAGES
DIVIDE_BY = (("1", "1"), ("2", "2"), ("5", "5"), ("10", "10"),
             ("25", "25"), ("50", "50"), ("100", "100"))
QUANTITY = (("5", "5"), ("10", "10"), ("20", "20"), ("30", "30"))
PRICE = (("0", "0%"), ("5", "5%"),  ("10", "10%"))
TEMPLATES = (('001-original', _l('Original')),)
EXPIRATIONS = (("30", "30 days"), ("90", "3 months"),
                   ("180", "6 months"), ("365", "1 year"))

def prim():
    return _l('Nice Label')+', 0.0001 BTC'

class TipForm(forms.Form):
    bcaddr = forms.CharField(max_length=90, required=True, label=_("Send to"), widget=forms.TextInput(
        attrs={'size': '90', 'placeholder': _l('Enter bitcoin address here'), 'style': 'border:1px solid red'}))
    bcamount = forms.CharField(required=False, help_text="all at the moment", widget=forms.TextInput(
        attrs={'readonly': 'readonly', 'class': 'disabled'}))

    def clean_bcaddr(self):
        bcaddr = self.cleaned_data['bcaddr']
        if len(bcaddr) < 30:
            raise forms.ValidationError(_('Your address seems too short'))
        if not re.match("^[A-Za-z0-9_-]*$", bcaddr):
            raise forms.ValidationError(_('Must be a valid Bitcoin Address'))
        valid = BITCOIND.validateaddress(bcaddr)['isvalid']
        if not valid:
            raise forms.ValidationError(_('Must be a valid Bitcoin Address'))
        return bcaddr


class WalletForm(forms.Form):
    bcaddr_from = forms.CharField(max_length=34, required=True, label=_(
        "Your Address"), widget=forms.TextInput)  # (attrs={'size':'34', 'style':'width:240px'})
    divide_currency = forms.ChoiceField(
        choices=CURRENCIES, widget=forms.Select())
    #target_language = forms.ChoiceField(choices=TARGET_LANGUAGES)
    divide_by = forms.ChoiceField(
        widget=forms.Select, choices=DIVIDE_BY, initial=2)
    quantity = forms.ChoiceField(widget=forms.Select, choices=QUANTITY)
    price = forms.ChoiceField(widget=forms.Select, choices=PRICE)
    message = forms.CharField(max_length=40, required=False, label=_(
        "Custom message"), widget=forms.TextInput(attrs={'size': '40'}))
    template = forms.ChoiceField(widget=forms.Select, choices=TEMPLATES)
    hashtag = forms.CharField(max_length=40, required=False)
    # p&p
    print_and_post = forms.BooleanField(required=False)
    address1 = forms.CharField(max_length=32, required=False)
    address2 = forms.CharField(max_length=32, required=False)
    city = forms.CharField(max_length=24, required=False)
    state = forms.CharField(max_length=24, initial='CA', required=False)
    country = forms.CharField(max_length=24, initial="USA", required=False,
                              widget=forms.TextInput(attrs={
                                  'readonly': 'readonly',
                                  'class': 'disabled'}))
    postal_code = forms.CharField(max_length=12, required=False)
    email = forms.CharField(max_length=64, required=False)
    expiration = forms.ChoiceField(
        widget=forms.Select, choices=EXPIRATIONS, initial="30")

    def clean_bcaddr_from(self):
        bcaddr_from = self.cleaned_data['bcaddr_from']
        if len(bcaddr_from) < 32:
            raise forms.ValidationError(_('Your address seems too short'))
        if not re.match("^[A-Za-z0-9_-]*$", bcaddr_from):
            raise forms.ValidationError(_('Must be a valid Bitcoin Address'))
        try:
            valid = BITCOIND.validateaddress(bcaddr_from)['isvalid']
        except:
            raise forms.ValidationError(_('Must be a valid Bitcoin Address'))
        if not valid:
            raise forms.ValidationError(_('Must be a valid Bitcoin Address'))
        return bcaddr_from

    def clean_divide_by(self):
        d = self.cleaned_data['divide_by']
        # d check if in DIVIDE_BY
        d = Decimal(d)
        return d

    def clean_quantity(self):
        return int(self.cleaned_data['quantity'])

    def clean_price(self):
        return Decimal(self.cleaned_data['price'])

    def clean_template(self):
        return self.cleaned_data['template']+'.odt'

    def clean_expiration(self):
        return int(self.cleaned_data['expiration'])


