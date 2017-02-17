# -*- coding: utf-8 -*-
from django.contrib import admin
from core.models import *

class TipInline(admin.TabularInline):
    model = Tip
    fields = ('key', 'activated', 'expired', 'miniid', 'ip', 'balance', 'comment')
    extra = 0

class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'atime', 'target_language', 'ip', 'price', 'hashtag', 'quantity', 'divide_by', 'divide_currency')
    search_fields = ['key', 'bcaddr']
    date_hierarchy = 'ctime'
    list_filter = ['activated', 'print_and_post', 'price', 'quantity', 'divide_by']
    inlines = [TipInline,]

class TipAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'key', 'balance', 'balance_usd', 'ip', 'activated', 'atime', 'comment')
    search_fields = ['key']
    list_filter = ['activated']
    date_hierarchy = 'atime'


admin.site.register(Wallet, WalletAdmin)
admin.site.register(Tip, TipAdmin)
#admin.site.register(Tip)

