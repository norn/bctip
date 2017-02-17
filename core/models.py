# -*- coding: utf-8 -*-

import json
import urllib2
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext as _
from jsonrpc import ServiceProxy

BITCOIND = ServiceProxy(settings.BITCOIND_CONNECTION_STRING)
"""
access.getbalance()
access.getinfo()
settxfee(0)
a.listaccounts()
a.listtransactions(acc)
"""
# 1 usd in rub
CURRENCY_RATES = {'USD': 1, 'EUR': 0.9, 'GBP': 0.66, 'SEK': 8.6, 'RUB': 70.0}
CURRENCY_SIGNS = {'USD': '$', 'EUR': '€', 'GBP': '£', 'SEK': 'kr'}
MESSAGES = {}
THANKS_MESSAGE = _("Thank you for your service!")
# Translators: Please provide youtube video about bitcoin in your language
LOCALIZED_YOUTUBE_URL = _("www.youtube.com/embed/Gc2en3nHxA4")


class Wallet(models.Model):
    key = models.CharField(max_length=64)  # secret
    ctime = models.DateTimeField(auto_now_add=True)
    # activation time (paid)
    atime = models.DateTimeField(null=True, blank=True)
    ip = models.IPAddressField(null=True, blank=True)
    ua = models.CharField(max_length=255, null=True, blank=True)
    bcaddr = models.CharField(max_length=34)  # pay to
    bcaddr_from = models.CharField(
        max_length=34, null=True, blank=True)  # paid from
    # target country: AU, US, RU. none for universal
    audience = models.CharField(max_length=2, null=True, blank=True)
    # amount of every tip, ex.:$2
    divide_by = models.DecimalField(
        decimal_places=8, max_digits=16, blank=True, null=True, default=0)
    divide_currency = models.CharField(
        max_length=3, default="USD")  # iso currency code
    quantity = models.SmallIntegerField(
        blank=True, null=True)  # how many
    template = models.CharField(
        max_length=34, default="001-original.odt")
    template_back = models.CharField(max_length=34, default="0000-default.odt")
    target_language = models.CharField(max_length=3, default="en")
    # custom message
    message = models.CharField(max_length=128, null=True, blank=True)
    # donation fee in percents
    price = models.DecimalField(decimal_places=2, max_digits=5, default="0")
    # tags for statistics
    hashtag = models.CharField(max_length=40, null=True, blank=True)
    # order print and post?
    print_and_post = models.BooleanField(default=False)
    # price of 1 BTC in target currency on this date
    rate = models.DecimalField(
        decimal_places=2, max_digits=10, blank=True, null=True, default=0)
    balance = models.BigIntegerField(null=True, blank=True)
    invoice = models.BigIntegerField(null=True, blank=True)
    activated = models.BooleanField(default=False)
    # expiration in days
    expiration = models.IntegerField(null=True, blank=True)
    src_site = models.SmallIntegerField(
        blank=True, null=True, default=0)  # for custom
    email = models.CharField(max_length=64, null=True, blank=True)

    @property
    def balance_nbtc(self):
        return self.balance / 100.0  # 1e3

    @property
    def balance_mbtc(self):
        return self.balance / 100000.0  # 1e5

    @property
    def balance_btc(self):
        if self.balance:
            return self.balance/100000000.0 or None  # 1e8
        else:
            return None

    @property
    def invoice_btc(self):
        if self.invoice != None:
            return self.invoice / 100000000.0  # 1e8
        else:
            return None

    @property
    def bcaddr_uri(self):
        return "bitcoin:%s?amount=%s&label=bctip.org" % (
            self.bcaddr, self.invoice_btc)

    @property
    def divide_currency_sign(self):
        return CURRENCY_SIGNS[self.divide_currency]

    def __unicode__(self):
        return u"%s" % (self.key)

    def get_absolute_url(self):
        return u"/w/%s/" % self.key

    def get_account(self):
        return "%s_%s" % (self.id, self.key[-6:])

    def activated_tips(self):
        return Tip.objects.filter(wallet=self, activated=True).count()

    @property
    def rate_fiat(self):
        return int(self.rate * Decimal(CURRENCY_RATES[self.divide_currency]))


class Address(models.Model):
    wallet = models.ForeignKey(Wallet)
    country = models.CharField(max_length=64, default="USA")
    state = models.CharField(max_length=64, null=True, blank=True)
    address1 = models.CharField("Address line 1", max_length=64)
    address2 = models.CharField(
        "Address line 2", max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, blank=False)
    postal_code = models.CharField("Postal Code", max_length=32)

    def __unicode__(self):
        return u"%s" % (self.country, self.city, self.address1)

    def get_absolute_url(self):
        return u"/admin/core/address/%d/" % self.id


class Tip(models.Model):
    wallet = models.ForeignKey(
        Wallet, null=True, blank=True)
    key = models.CharField(max_length=64, null=True, blank=True)
    ctime = models.DateTimeField(
        auto_now_add=True, null=True, blank=True)
    # activation
    atime = models.DateTimeField(null=True, blank=True)
    # expiration
    etime = models.DateTimeField(null=True, blank=True)
    ip = models.IPAddressField(null=True, blank=True)  # пока не исп
    ua = models.CharField(max_length=255, null=True, blank=True)  # user agent
    balance = models.BigIntegerField(
        blank=True, null=True, default=0)
    miniid = models.CharField(max_length=4)
    comment = models.CharField(max_length=40, default="")
    comment_time = models.DateTimeField(null=True, blank=True)
    activated = models.BooleanField(default=False)
    expired = models.BooleanField(default=False)
    bcaddr = models.CharField(max_length=34, null=True, blank=True)
    txid = models.CharField(max_length=64, null=True, blank=True)
    # tip page visit counter
    times = models.IntegerField(null=True, blank=True, default=0)

    def __unicode__(self):
        return u"%s: %s" % (self.wallet, self.balance_btc)

    def get_absolute_url(self):
        domain = "https://www.bctip.org"
        return "%s/%s/" % (domain, self.key)

    @property
    def balance_nbtc(self):
        return self.balance / 100.0  # 1e3

    @property
    def balance_mbtc(self):
        return self.balance / 100000.0  # 1e5

    @property
    def balance_btc(self):
        return self.balance / 100000000.0  # 1e8

    @property
    def balance_usd(self):
        return round(self.balance_btc * get_avg_rate(), 2)

    @property
    def balance_eur(self):
        return round(self.balance_btc * get_avg_rate_euro(), 2)

    @property
    def balance_fiat(self):
        fiat = Decimal(self.balance_usd) * \
            Decimal(CURRENCY_RATES[self.wallet.divide_currency])
        return round(fiat, 2)


def get_avg_rate():
    rate = get_bitstamp_avg_rate()
    if rate:
        return rate
    rate = get_coinbase_avg_rate()
    if rate:
        return rate

    return 770.0  # if everything failed


def get_avg_rate_euro():
    rate = get_avg_rate()
    return int(rate*CURRENCY_RATES['EUR'])

"""
def get_mtgox_avg_rate():
    try:
        mtgox = urllib2.urlopen("https://data.mtgox.com/api/1/BTCUSD/ticker", timeout=5).read()
        mtgox = json.loads(mtgox)
        return float(mtgox['return']['avg']['value'])
    except:
        return None
"""


def get_btce_avg_rate(force=False):
    key = 'avg_rate_btce'
    rate = cache.get(key)
    if rate and not force:
        return rate
    try:
        btce = urllib2.urlopen(
            "https://btc-e.com/api/2/btc_usd/ticker", timeout=4).read()
        btce = json.loads(btce)
        rate = float(btce['ticker']['avg'])
        cache.set(key, rate, 60*60)  # cache for an hour
        return rate
    except:
        return None


def get_coinbase_avg_rate(force=False):
    key = 'avg_rate__coinbase'
    rate = cache.get(key)
    if rate and not force:
        return rate
    try:
        coinbase = urllib2.urlopen(
            "https://coinbase.com/api/v1/prices/buy", timeout=4).read()
        coinbase = json.loads(coinbase)
        rate = float(coinbase['total']['amount'])
        cache.set(key, rate, 60*60)  # cache for an hour
        return rate
    except:
        return None


def get_bitstamp_avg_rate(force=False):
    key = 'avg_rate__bitstamp'
    rate = cache.get(key)
    if rate and not force:
        return rate
    try:
        bitstamp = urllib2.urlopen(
            "https://www.bitstamp.net/api/ticker/", timeout=4).read()
        bitstamp = json.loads(bitstamp)
        rate = int((float(bitstamp['high'])+float(bitstamp['low']))/2.0)
        cache.set(key, rate, 60*60)  # cache for an hour
        return rate
    except:
        return None
