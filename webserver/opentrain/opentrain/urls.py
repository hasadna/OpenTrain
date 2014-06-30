from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import RedirectView
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'opentrain.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$',RedirectView.as_view(url='/timetable/search-in/')),
    url(r'^timetable/',include('timetable.urls',namespace='timetable')),
    url(r'^reports/',include('reports.urls')),
    url(r'^client/',include('client.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^analysis/',include('analysis.urls',namespace='analysis')),
    url(r'^api/1/',include('ot_api.urls',namespace='ot_api')),
    url(r'^static/jsi18n/he/django.js$', 'common.views.home'),
    url(r'^privacy','common.views.privacy')
)

