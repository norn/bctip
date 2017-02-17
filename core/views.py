# -*- coding: utf-8 -*-
import calendar
import datetime
import json
import os
import pickle
import random
import shutil
import StringIO
import time
import urllib
import zipfile
from decimal import Decimal

import qrcode
from core.forms import *
from core.models import *
from core.tasks import celery_generate_pdf
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db.models import Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, render_to_response
from django.template import Context, RequestContext, Template
from django.utils.translation import ugettext as _

BASE10 = '1234567890'
BASE58 = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
DEFAULT_EXP = datetime.timedelta(days=30)
EST_FEE = 0.0003


def arender(request, template, ctx):
    return render(request, template, ctx)


def get_random_key(base=BASE58, length=33):
    key = ""
    for i in range(0, length):
        key += base[random.randint(0, len(base)-1)]
    return key


def generate_tips(wallet):
    quant = wallet.divide_by/wallet.rate / \
        Decimal(CURRENCY_RATES[wallet.divide_currency])*Decimal(1e8)
    quant = int(quant)

    for i in range(0, wallet.quantity):
        key = ""
        for j in range(3):
            key += "%s-" % get_random_key(length=4)
        key = key.lower()[:-1]
        Tip.objects.create(
            wallet=wallet, key=key, etime=datetime.datetime.now()+DEFAULT_EXP, balance=quant)
    return True

# views


def home(request, template="index.html"):
    site = request.META.get('HTTP_HOST', '').lower()
    ctx = {}
    template = "index.html"
    return arender(request, template, ctx)


def download(request, key, format, page_size="A4"):
    wallet = get_object_or_404(Wallet, key=key)
    page_size_prefix = ""
    if page_size == "US":
        page_size_prefix = "us-"
    fn = '/static/%s/tips-%s%s.%s' % (format,
                                      page_size_prefix, wallet.key, format)
    i = 0

    while not os.path.exists("%s/%s" % (settings.PROJECT_DIR, fn)):
        if i == 0:
            result = celery_generate_pdf.delay(wallet)
            time.sleep(25)
        if i > 0:
            ctx = {'result': result.ready(), 'info': result.info}
            return render_to_response("not_yet.html", context_instance=RequestContext(request, ctx))
        i += 1

    return HttpResponseRedirect(fn)


def new(request):
    site = request.get_host()
    key = get_random_key()
    src_site = 0
    ua = request.META.get('HTTP_USER_AGENT')
    ip_ = request.META.get('HTTP_X_FORWARDED_FOR')
    if ',' in ip_:
        ip_ = ip_.split(", ")[0]
    avg_rate = get_avg_rate()
    wallet = Wallet.objects.create(
            key=key, ip=ip_, rate=avg_rate, ua=ua[:255], src_site=src_site)
    wallet.save()
    url = reverse('wallet', kwargs={'key': wallet.key})
    return HttpResponseRedirect(url)


def statistics(request):
    tips = Tip.objects.filter(
        wallet__atime__isnull=False, wallet__activated=True)
    tips_expired = Tip.objects.filter(expired=True)
    tips_sum = tips.aggregate(Sum('balance'))['balance__sum']
    tips_sum_a = tips.filter(activated=True).aggregate(
        Sum('balance'))['balance__sum']
    if not tips_sum_a:
        tips_sum_a = 0
    if tips:
        # tips_sum_a*100.0/tips_sum
        asrate = tips.filter(activated=True).count() * 100 / tips.count()
    tips_sum = Tip(balance=tips_sum)
    tips_sum_a = Tip(balance=tips_sum_a)

    now = datetime.datetime.now()
    mnames = []
    tips_per_month = []
    tips_per_month_all = []
    for month in range(0, 12):
        c = now - datetime.timedelta(days=30*month)
        mnames.insert(0, c.strftime("%B %Y"))
        tips_per_month.insert(
            0, Tip.objects.filter(atime__year=c.year, atime__month=c.month).count())
        tips_per_month_all.insert(
            0, Tip.objects.filter(ctime__year=c.year, ctime__month=c.month).count())
    mnames = json.dumps(mnames)
    tips_per_month = json.dumps(tips_per_month)

    day_names = []
    tips_per_day = []
    now = datetime.datetime(year=now.year, month=now.month, day=1)
    for day in range(0, calendar.monthrange(now.year, now.month)[1]):
        c = now+datetime.timedelta(days=day)
        #day_names.append(c.strftime("%d %B %Y"))
        day_names.append(c.strftime("%d"))
        tips_per_day.append(Tip.objects.filter(
            atime__year=c.year, atime__month=c.month, atime__day=c.day).count())
    day_names = json.dumps(day_names)
    tips_per_day = json.dumps(tips_per_day)

    ctx = {'tips': tips.count(), 'tips_a': tips.filter(activated=True).count(),
           'tips_sum': tips_sum, 'tips_sum_a': tips_sum_a, 'activation_success': asrate,
           'tips_expired': tips_expired.count(),
           'mnames': mnames, "day_names": day_names,
           'tips_per_month': tips_per_month, 'tips_per_month_all': tips_per_month_all, "tips_per_day": tips_per_day}

    return arender(request, 'statistics.html', ctx)


def wallet(request, key):
    site = request.META.get('HTTP_HOST', '').lower()

    wallet = get_object_or_404(Wallet, key=key)
    #custom = request.GET.get("c")
    ctx = {'wallet': wallet, 'json_rates': json.dumps(CURRENCY_RATES), 'json_messages': json.dumps(
        MESSAGES), 'json_signs': json.dumps(CURRENCY_SIGNS)}
    if wallet.atime:  # if already paid and activated
        return private(request, key, wallet)

    # Check if it was paid
    if wallet.bcaddr and not wallet.atime:
        balance = BITCOIND.getbalance(wallet.get_account(), 0)
        if balance and balance >= wallet.invoice_btc:
            wallet.atime = datetime.datetime.now()
            wallet.activated = True
            wallet.balance = balance*1e8

            # get our fees
            if wallet.price:
                fee = wallet.divide_by*wallet.quantity  # pure tips
                fee = fee/100*wallet.price
                fee = fee/wallet.rate
                if wallet.template == "005-premium.odt":
                    fee += Decimal("0.002")
            if wallet.print_and_post:
                pap_total = 2+wallet.quantity/9.0*1
                pap_total = pap_total/wallet.rate
                pap_total = round(pap_total, 8)
            wallet.save()
            if wallet.email:
                send_mail('new BCTIP wallet', 'Congratulations!\n\nYour new BCTip wallet is available at: https://www.bctip.org/w/%s/' %
                          (wallet.key), 'noreply@bctip.org', [wallet.email], fail_silently=True)
            return HttpResponseRedirect(reverse('wallet', kwargs={'key': wallet.key}))

    if request.POST:
        form = WalletForm(request.POST)
        if form.is_valid():
            wallet.bcaddr_from = form.cleaned_data['bcaddr_from']
            wallet.divide_by = form.cleaned_data['divide_by']
            wallet.quantity = form.cleaned_data['quantity']
            wallet.price = form.cleaned_data['price']
            wallet.message = form.cleaned_data['message']
            wallet.template = form.cleaned_data['template']
            wallet.divide_currency = form.cleaned_data['divide_currency']
            # request.form.cleaned_data['target_language']
            wallet.target_language = request.LANGUAGE_CODE
            wallet.email = form.cleaned_data['email']

            total_usd = wallet.divide_by*Decimal(wallet.quantity)  # pure tips
            # tips and price for service
            total_usd = total_usd+total_usd/Decimal(100)*wallet.price

            if form.cleaned_data['print_and_post']:
                wallet.print_and_post = True
                pap_total = 2+wallet.quantity/9.0*1  # 2 + 1 for each sheet
                total_usd += Decimal(pap_total)
                a = Address(wallet=wallet)
                a.address1 = form.cleaned_data['address1']
                a.address2 = form.cleaned_data['address2']
                a.city = form.cleaned_data['city']
                a.state = form.cleaned_data['state']
                a.country = form.cleaned_data['country']
                a.postal_code = form.cleaned_data['postal_code']
                a.save()  # чу-чо!
            wallet.invoice = total_usd/wallet.rate / \
                Decimal(
                    CURRENCY_RATES[wallet.divide_currency])*Decimal(1e8)  # usd->btc
            wallet.invoice += Decimal(1+wallet.quantity) * \
                Decimal(EST_FEE)*Decimal(1e8)
            # premium template extra
            if wallet.template == "005-premium.odt":
                wallet.invoice += Decimal(0.002)*Decimal(1e8)
            wallet.bcaddr = BITCOIND.getnewaddress(wallet.get_account())
            isvalid = BITCOIND.validateaddress(wallet.bcaddr_from)['isvalid']
            wallet.save()
            generate_tips(wallet)
            celery_generate_pdf.delay(wallet)
            response = HttpResponseRedirect(
                reverse('wallet', kwargs={'key': wallet.key}))
            if wallet.email:
                email = pickle.dumps(wallet.email, protocol=0)
                response.set_cookie('email', email)
            response.set_cookie('bcaddr_from', wallet.bcaddr_from)
            return response
    else:
        initial = {'divide_currency': 'USD', 'divide_by': 5, 'quantity': 10, 'price':
                   "5", "template": '001-original', "message": _('Thank you for your service!')}
        email = request.COOKIES.get('email')
        if email:
            try:
                email = pickle.loads(email)
            except:
                pass
            initial['email'] = email
        bcaddr_from = request.COOKIES.get('bcaddr_from')
        if bcaddr_from:
            initial['bcaddr_from'] = bcaddr_from

        form = WalletForm(initial=initial)
    ctx['form'] = form
    if wallet.bcaddr and not wallet.atime:
        return arender(request, 'wallet-new-unpaid.html', ctx)
    else:
        return arender(request, 'wallet-new.html', ctx)


def wajax(request, key):  # no processing here, just a period checking
    wallet = get_object_or_404(Wallet, key=key)
    if not wallet.atime:
        balance = BITCOIND.getbalance(wallet.get_account(), 0)
        if balance and balance >= wallet.invoice_btc:
            return HttpResponse('1')
        else:
            return HttpResponse('0')
    else:
        return HttpResponse('1')


def qrcode_view(request, key):
    wallet = get_object_or_404(Wallet, key=key)
    img = qrcode.make(
        wallet.bcaddr_uri, box_size=6, error_correction=qrcode.ERROR_CORRECT_M)
    output = StringIO.StringIO()
    img.save(output, "PNG")
    c = output.getvalue()
    return HttpResponse(c, content_type="image/png")


def tip(request, key):
    tip = get_object_or_404(Tip, key=key)
    tip.times += 1
    tip.save()
    tip_bcaddr = None

    if request.POST and not tip.activated and not tip.expired:
        form = TipForm(request.POST)
        if form.is_valid():
            cc_key = 'lock_%s' % tip.id
            while cache.get(cc_key):
                time.sleep(x)
            cache.set(cc_key, 1, 3)
            tip = get_object_or_404(Tip, key=key)  # one more
            if tip.activated:
                return HttpResponse("Timeout error")
            # just check
            if BITCOIND.getbalance(tip.wallet.get_account(), 5) < tip.balance_btc:
                return render_to_response("not_enough.html", context_instance=RequestContext(request, {}))
            tip.atime = datetime.datetime.now()
            tip.activated = True
            tip.bcaddr = form.cleaned_data['bcaddr']
            tip.ip = request.META.get('HTTP_X_FORWARDED_FOR')
            tip.ua = request.META.get('HTTP_USER_AGENT')
            tip.save()
            tip.txid = BITCOIND.sendfrom(
                tip.wallet.get_account(), tip.bcaddr, tip.balance_btc)
            tip.save()
            cache.set(cc_key, None)
            if tip.wallet.email:
                wcomment = ""
                if tip.comment:
                    wcomment = 'with comment "%s" ' % tip.comment
                send_mail('Bitcoin tips has been activated', 'BCTip https://www.bctip.org/%s/ %shas been activated.' %
                          (tip.key, wcomment), 'noreply@bctip.org', [tip.wallet.email], fail_silently=True)
            tip_bcaddr = tip.bcaddr
    else:
        initial = {'bcamount': tip.balance_btc}
        tip_bcaddr = request.COOKIES.get('tip_bcaddr')
        if tip_bcaddr:
            initial['bcaddr'] = tip_bcaddr
        form = TipForm(initial=initial)
    ctx = {'tip': tip, 'rate': get_avg_rate(), 'form': form}
    template = "tip.html"
    response = render_to_response(
        template, context_instance=RequestContext(request, ctx))
    if tip_bcaddr:
        response.set_cookie('tip_bcaddr', tip_bcaddr)
    return response


def private(request, key, wallet):
    tips = Tip.objects.filter(wallet=wallet).order_by('id')
    wallet_ready = False
    delta = datetime.datetime.now()-wallet.atime.replace(tzinfo=None)
    if delta.seconds > 45:
        wallet_ready = True
    ctx = {'wallet': wallet, 'tips': tips, 'rate':
           get_avg_rate(), 'wallet_ready': wallet_ready, 'delta': delta.seconds}
    return arender(request, 'wallet.html', ctx)


def comments(request, key):
    wallet = get_object_or_404(Wallet, key=key)
    ctx = {'wallet': wallet}
    # Save comments for already paid wallet
    if request.POST:
        for k, v in request.POST.iteritems():
            if not k.startswith('cmnt'):
                continue
            k = int(k.lstrip('cmnt'))
            tip = Tip.objects.get(id=k, wallet__key=key)
            if tip.comment != v:
                tip.comment = v[:40]
                tip.comment_time = datetime.datetime.now()
                tip.save()
    return HttpResponseRedirect(reverse('wallet', kwargs={'key': wallet.key}))


def tip_redir(request, key):
    return HttpResponseRedirect("/%s/" % key)


def tips_example(request):
    tip_bcaddr = None
    tip = Tip(key="abcd-efgh-ijkl-mnop", balance=1234567,
              etime=datetime.datetime.now()+DEFAULT_EXP)
    initial = {'bcamount': tip.balance_btc}
    form = TipForm(initial=initial)
    ctx = {
        'tip': tip, 'rate': get_avg_rate(), 'form': form, "tips_example": True}
    template = "tip.html"
    response = render_to_response(
        template, context_instance=RequestContext(request, ctx))
    return response
