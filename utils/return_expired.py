#!/usr/bin/python
# -*- coding: utf-8 -*-

from devinclude import *
from core.models import *
import datetime
from jsonrpc import ServiceProxy
from django.db.models import Sum
from django.core.mail import send_mail

BITCOIND = ServiceProxy(settings.BITCOIND_CONNECTION_STRING)
BITCOIND.settxfee(0)

now = datetime.datetime.now()
expired_tips = Tip.objects.filter(etime__lt=now, activated=False, wallet__activated=True, expired=False).order_by('wallet')

# Step 1: move all the stuff to the special expired account
expired=[]
for tip in expired_tips:
    account = tip.wallet.get_account()
    BITCOIND.move(account, account+"_exp", tip.balance_btc+tip.wallet.fee_float)
    #print "BITCOINDD move(%s) %s, %s, %s"%(BITCOIND.getbalance(account),,account, account+"_exp", tip.balance_btc)
    if account not in expired:
        expired.append(account)
    tip.expired=True
    tip.save()

# Step 2: get all the money from epxpired accounts and return to the wallet owner
for account in expired:
    amount = BITCOIND.getbalance(account+"_exp")
    wallet_id = int(account.split('_')[0])
    wallet = Wallet.objects.get(id=wallet_id)
    BITCOIND.settxfee(wallet.fee_float)
    txid = BITCOIND.sendfrom(account+"_exp", wallet.bcaddr_from, amount-wallet.fee_float)
    print "BITCOIND sendfrom(%s, %s, %s)"%(account+"_exp", wallet.bcaddr_from, amount-wallet.fee_float)
    # manage txid
    Tip.objects.filter(wallet=wallet, expired=True).update(txid=txid)
    if wallet.email:
        send_mail('BCTip wallet was expired', 'Tips from wallet https://www.bctip.org/w/%s/ were expired. \nUnused bitcoins were sent to your address %s'%(wallet.key, wallet.bcaddr_from), 'noreply@bctip.org', [wallet.email], fail_silently=True)

# Step 3: Debit/Credit balance check
#Tip.objects.filter(wallet__atime__gte='2014-08-01', activated=False)
credit = Tip.objects.filter(wallet__activated=True, activated=False, expired=False).aggregate(Sum('balance'))['balance__sum']
if not credit:
    credit = 0
else:
    credit = credit/1e8
print "Credit(dolg): %s Balance: %s"%(credit, BITCOIND.getbalance())
