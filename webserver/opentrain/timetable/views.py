from django.http import HttpResponse
import datetime
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View
from django.core.urlresolvers import reverse

import models
import common.ot_utils
import services

from models import TtTrip,TtStop
 
def show_map(req,gtfs_trip_id):
    ctx = dict()
    zoom_stop_id = req.GET.get('zoom_stop_id',0)
    if zoom_stop_id > 0:
        ctx['zoom_stop'] = TtStop.objects.get(gtfs_stop_id=zoom_stop_id)
    else:
        ctx['zoom_stop'] = None
    ctx['trip'] = TtTrip.objects.get(gtfs_trip_id=gtfs_trip_id)
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

def show_gtfs_files(req):
    import glob
    from django.conf import settings
    import os.path
    ctx = dict()
    base_dirs = [os.path.join(settings.BASE_DIR,'tmp_data/gtfs/zip_data/'),
                 os.path.join(settings.BASE_DIR,'tmp_data/gtfs/data')]
    zip_files = []
    for bd in base_dirs:
        zip_files.extend(glob.glob(os.path.join(bd,'*/*.zip')))
    gtfs_files = []
    for zp in zip_files:
        if zp.startswith(settings.BASE_DIR):
            zp_url = zp[len(settings.BASE_DIR):].replace('tmp_data','timetable/old-gtfs-files')
        else:
            zp_url = 'none'
        gtfs_files.append(dict(path=zp,
                               url=zp_url))
        gtfs_files.sort(key=lambda x : x['path'])
    ctx['gtfs_files'] = gtfs_files
    return render(req,'timetable/gtfs_files.html',ctx)


def show_distances(req):
    import services
    ctx = dict()
    stops = list(TtStop.objects.all().order_by('gtfs_stop_id'))
    ctx['stops'] = stops
    dists = services.get_dists_matrix()
    dists_dict = dict()
    for dist in dists:
        dists_dict[(dist['gtfs_stop_id1'],dist['gtfs_stop_id2'])] = dist
        dists_dict[(dist['gtfs_stop_id2'],dist['gtfs_stop_id1'])] = dist
    rows = []
    for stop1 in stops:
        row = dict(stop=stop1)
        cells = []
        for stop2 in stops:
            dist_entry =  dists_dict.get((stop1.gtfs_stop_id,stop2.gtfs_stop_id))
            if dist_entry:
                cells.append(dist_entry)
            else:
                cells.append(None)
        row['cells'] = cells
        rows.append(row)
    ctx['rows'] = rows
    return render(req,'timetable/distances.html',ctx)

