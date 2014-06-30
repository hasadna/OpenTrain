from django.http import HttpResponse
import datetime
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View
from django.core.urlresolvers import reverse

import models
import common.ot_utils
import services
 
def show_map(req,trip_id):
    ctx = dict()
    zoom_stop_id = req.GET.get('zoom_stop_id',0)
    if zoom_stop_id > 0:
        ctx['zoom_stop'] = models.Stop.objects.get(stop_id=zoom_stop_id)
    else:
        ctx['zoom_stop'] = None
    ctx['trip'] = models.Trip.objects.get(trip_id=trip_id)
    return render(req, 'timetable/trip_map.html', ctx)

from forms import SearchInForm
class TimeTableSearchIn(View):
    url_name = 'timetable:search-in'
    fields = ['in_station','when','before','after']
    title = 'Search In'

    def get(self,req,*args,**kwargs):
        ctx = dict()
        initial = dict()
        defaultForm = dict(when=datetime.datetime.now(),before=30,after=30)
        for f in self.fields:
            value = req.GET.get(f,None)
            if value:
                if f == 'when':
                    initial[f] = common.ot_utils.parse_form_date(value)
                else:
                    initial[f] = value
                
        form = SearchInForm(initial=initial if initial else defaultForm)
        ctx['form'] = form        
        ctx['title'] = self.title
        ctx['url_name'] = self.url_name 
        if initial: 
            ctx['when'] = initial['when']
            ctx['results'] = services.do_search(**initial) 
        return render(req, 'timetable/search_form.html', ctx)
    
    def post(self,req,*args,**kwargs):
        import urllib
        form = SearchInForm(req.POST)
        if form.is_valid():
            params = dict()
            params.update(form.cleaned_data)
            params['when'] = req.POST['when']
            qs = urllib.urlencode(params)
            url = reverse(self.url_name)
            return HttpResponseRedirect('%s?%s' % (url,qs))
        raise Exception('Illegal Form')


