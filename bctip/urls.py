from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.contrib import admin
from django.conf import settings
admin.autodiscover()

urlpatterns = i18n_patterns('',
    url(r'^$', 'core.views.home', name='home'),
    url(r'^new/$', 'core.views.new', name='new'),
    url(r'^statistics/$', 'core.views.statistics', name='statistics'),
    url(r'^(?P<key>\w+-\w+-\w+-\w+-\w+)$', 'core.views.tip_redir'),
    url(r'^(?P<key>\w+-\w+-\w+-\w+-\w+)/$', 'core.views.tip'),
    url(r'^(?P<key>\w+-\w+-\w+)$', 'core.views.tip_redir', name='tip_redir'),
    url(r'^(?P<key>\w+-\w+-\w+)/$', 'core.views.tip', name='tip'),
    url(r'^gratuity-example/$', 'core.views.tips_example', name='tips_example'),
    url(r'^w/(?P<key>\w+)/$', 'core.views.wallet', name='wallet'),
    url(r'^w/(?P<key>\w+)/comments/$', 'core.views.comments', name='comments'),
    url(r'^w/(?P<key>\w+)/wajax/$', 'core.views.wajax', name='wajax'),
    url(r'^w/(?P<key>\w+)/print/$', 'core.views.printHTML', name='printHTML'),
)

urlpatterns += patterns('',
    #url(r'^admin/', include(admin.site.urls)),
    url(r'qrcode/(?P<key>\w+)/$','core.views.qrcode_view', name='qrcode'),
)

if settings.BCTIP_MOD:
    import bctip.urls_custom
urlpatterns += bctip.urls_custom.urlpatterns