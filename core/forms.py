# -*- coding: utf-8 -*-
from django import forms
from core.models import *
import re
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l
from django.conf import settings

CURRENCIES = (('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY'))
TARGET_LANGUAGES = settings.LANGUAGES
DIVIDE_BY = (("1", "1"), ("2", "2"), ("5", "5"), ("10", "10"),
             ("25", "25"), ("50", "50"), ("100", "100"))
DIVIDE_BY_JPY = (("100", "100"), ("200", "200"), ("500", "500"), ("1000", "1,000"),
             ("2500", "2,500"), ("5,000", "5,000"), ("10000", "10,000"))
QUANTITY = (("1", "1"), ("5", "5"), ("10", "10"), ("20", "20"), ("30", "30"))
PRICE = (("1", "1%"), ("3", "3%"),  ("0", "Custom"))
TEMPLATES = (('001-original', _l('Original')),)
EXPIRATIONS = (("30", "30 days"), ("90", "3 months"),
                   ("180", "6 months"), ("365", "1 year"))

def prim():
    return _l('Nice Label')+', 0.0001 BTC'

class TipForm(forms.Form):
    bcaddr = forms.CharField(max_length=100, required=True, label=_("Send to"), widget=forms.TextInput(
        attrs={'size': '100', 'placeholder': _l('Enter Bitcoin Cash (BCH) address here'), 'style': 'border:1px solid #fab915;'}))
    bcamount = forms.CharField(required=False, help_text="all at the moment", widget=forms.TextInput(
        attrs={'readonly': 'readonly', 'class': 'disabled'}))

    def clean_bcaddr(self):
        bcaddr = self.cleaned_data['bcaddr']
        if len(bcaddr) < 30:
            raise forms.ValidationError(_('ERROR: Your address seems too short. Please use a valid Bitcoin Cash (BCH) address including prefix \"bitcoincash:\"'))        

        if not "bitcoincash:" in bcaddr:
            raise forms.ValidationError(_('ERROR: To prevent confusion with Bitcoin Core (BTC), only Bitcoin Cash (BCH) addresses in Cash Address format including prefix \"bitcoincash:\" can be accepted'))


        #Cashaddr validation using bitcoin node
        valid = BITCOIND.validateaddress(bcaddr)['isvalid']
        if not valid:
            raise forms.ValidationError(_('ERROR: Must be a valid Bitcoin Cash (BCH) Address'))

        return bcaddr


class WalletForm(forms.Form):
    #Put maxlength to 100, from 34 for legacy addresses
    bcaddr_from = forms.CharField(max_length=100, required=True, label=_(
        "Your Address"), widget=forms.TextInput)  # (attrs={'size':'34', 'style':'width:240px'})
    divide_currency = forms.ChoiceField(
        choices=CURRENCIES, widget=forms.Select())
    #target_language = forms.ChoiceField(choices=TARGET_LANGUAGES)
    divide_by = forms.ChoiceField(
        widget=forms.Select, choices=DIVIDE_BY, initial=2)
    divide_by_jpy = forms.ChoiceField(
        widget=forms.Select, choices=DIVIDE_BY_JPY, initial=500)
    quantity = forms.ChoiceField(widget=forms.Select, choices=QUANTITY)
    price = forms.ChoiceField(widget=forms.Select, choices=PRICE)
    customprice = forms.IntegerField(initial="5",min_value=0, max_value=25, required=False)
    message = forms.CharField(max_length=40, required=False, label=_(
        "Custom message"), widget=forms.TextInput(attrs={'size': '40'}))
    template = forms.ChoiceField(widget=forms.Select, choices=TEMPLATES)
    hashtag = forms.CharField(max_length=40, required=False)
    # p&p
    # Not expected to be used for tips.bitcoin.com
    # Leave in to avoid database changes, may be used in the future
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
            raise forms.ValidationError(_('ERROR: Your address seems too short. Please use a valid Bitcoin Cash (BCH) address including prefix \"bitcoincash:\"'))
        #Skip this validation since want to support cashaddr
        #if not re.match("^[A-Za-z0-9_-]*$", bcaddr_from):
        #    raise forms.ValidationError(_('Must be a valid Bitcoin Cash (BCH) Address'))
        if not "bitcoincash:" in bcaddr_from:
            raise forms.ValidationError(_('ERROR: To prevent confusion with Bitcoin Core (BTC), only Bitcoin Cash (BCH) addresses in Cash Address format including prefix \"bitcoincash:\" can be accepted'))

        try:
            valid = BITCOIND.validateaddress(bcaddr_from)['isvalid']
        except:
            raise forms.ValidationError(_('ERROR: Must be a valid Bitcoin Cash (BCH) Address'))
        if not valid:
            raise forms.ValidationError(_('ERROR: Must be a valid Bitcoin Cash (BCH) Address'))
        return bcaddr_from

    def clean_divide_by(self):
        d = self.cleaned_data['divide_by']
        # d check if in DIVIDE_BY
        d = Decimal(d)
        return d

    def clean_divide_by_jpy(self):
        d = self.cleaned_data['divide_by_jpy']
        # d check if in DIVIDE_BY
        d = Decimal(d)
        return d

    def clean_quantity(self):
        return int(self.cleaned_data['quantity'])

    def clean_customprice(self):
        #Handle case where user has left the form blank
        if self.cleaned_data['customprice'] is None:
            return 0
        return Decimal(self.cleaned_data['customprice'])

    def clean_price(self):
        return Decimal(self.cleaned_data['price'])

    def clean_template(self):
        return self.cleaned_data['template']+'.odt'

    def clean_expiration(self):
        return int(self.cleaned_data['expiration'])