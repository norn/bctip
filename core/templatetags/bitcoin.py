# -*- coding: utf-8 -*-
from django import template
register = template.Library()
from core.models import CURRENCY_RATES

@register.filter(name='btc')
def btc(value):
    return value/1e8

@register.filter(name='mbtc')
def mbtc(value):
    return value/1e5

@register.filter(name='nbtc')
def nbtc(value):
    return value/1e3

@register.filter(name='usd')
def usd(value):
    return value/1e8
