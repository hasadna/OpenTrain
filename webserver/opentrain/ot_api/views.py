import json
import common.ot_utils
import datetime
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.conf import settings
import urllib

from django.views.generic import View
from django.shortcuts import render

def show_docs(request):
    ctx = dict()
    ctx['apis'] = ApiView.get_api_insts()
    
    return render(request,'ot_api/docs.html',ctx)

class ApiView(View):
    def _prepare_list_resp(self,req,items,info=None):
        info = info or dict()
        count = len(items)
        total_count = info.get('total_count',len(items))
        meta=dict(count=count,total_count=total_count)
        if total_count > count:
            if total_count > info['offset'] + info['limit']:
                d = req.GET.dict()
                d['offset'] = info['offset'] + info['limit']
                meta['next'] = req.path + '?' + urllib.urlencode(d)
        content = dict(objects=items,meta=meta)
        return HttpResponse(content=json.dumps(content),content_type='application/json',status=200)


    def get_json_resp(self,content,status=200):
        return HttpResponse(content=json.dumps(content),content_type='application/json',status=status)


    def get_bool(self,key,defval=None):
        val = self.GET.get(key,None)
        if val is None:
            return defval
        val = val.lower()
        if val == 'false':
            return False
        if val == 'true':
            return True
        return bool(int(val))



    def get_doc(self):
        return self.__doc__
    
    def get_api_url_nice(self):
        u = self.api_url
        u =  u.replace('$','').replace('^','')
        u = '/api/1/' + u
        return u
    
    @classmethod
    def get_api_insts(cls):
        return [c() for c in cls.get_api_classes()]
    
    @classmethod
    def get_api_classes(cls):
        return cls.__subclasses__()
    
    
    @classmethod
    def get_urls(cls):
        from django.conf.urls import url
        urls = []
        for ac in cls.get_api_classes():
            urls.append(url(ac.api_url,ac.as_view()))
        return urls
    
class TripIdsForDate(ApiView):
    """ Return list of trips for given date given 
        paramters: one of:
                 date : in format dd/mm/yyyy 
                 today : 0/1         
        """
    api_url = r'^trips/trips-for-date/$'
    def get(self,request):
        import timetable.services
        date = request.GET.get('date')
        today = self.get_bool('today',False)
        if not today and not date:
            raise Exception('Must have either today or date')
        if today:
            dt = common.ot_utils.get_localtime_now().date()
        else:
            day,month,year = date.split('/')
            dt = datetime.date(year=int(year),month=int(month),day=int(day))
        trips = timetable.services.get_all_trips_in_date(dt)
        objects=[trip.gtfs_trip_id for trip in trips]
        result = dict(objects=objects,
                      meta=dict(total_count=len(objects)))
        return self.get_json_resp(result)

class TripDetails(ApiView):
    """ Return details for trip with id trip_id (given in url)
        details include the points in order to draw the trip on map
    """
    api_url = r'^trips/(?P<gtfs_trip_id>\w+)/details/$'
    def get(self,request,gtfs_trip_id):
        import timetable.services
        trip = timetable.services.get_trip(gtfs_trip_id)
        result = trip.to_json_full()
        return self.get_json_resp(result)

class TripDetails(ApiView):
    """ Return details for trip with id trip_id (given in url)
        details include the points in order to draw the trip on map
    """
    api_url = r'^trips/(?P<gtfs_trip_id>\w+)/stops/$'
    def get(self,request,gtfs_trip_id):
        import timetable.services
        from analysis.models import RtStop
        device_id = request.GET.get('device_id')
        if device_id is None:
            return HttpResponseBadRequest('Must specify device_id')
        trip = timetable.services.get_trip(gtfs_trip_id)
        rt_stops = RtStop.objects.filter(tracker_id=device_id,trip__gtfs_trip_id=gtfs_trip_id)
        result = trip.to_json_full(with_shapes=False,rt_stops=rt_stops)
        return self.get_json_resp(result)


class CurrentTrips(ApiView):
    """ Return current trips """
    api_url = r'^trips/current/$'
    def get(self,request):
        import analysis.logic
        current_trips = analysis.logic.get_current_trips()    
        return self._prepare_list_resp(request, current_trips)

class TripsLocation(ApiView):
    """ Return location (exp and cur) of trips given in comma separated GET paramter trip_ids """
    api_url = r'^trips/cur-location/$'
    def get(self,request):
        import analysis.logic
        trip_ids = request.GET.get('trip_ids',None)
        if not trip_ids:
            return HttpResponseBadRequest('Must specify trip_ids')
        live_trips = analysis.logic.get_trips_location(trip_ids.split(','))     
        result = dict(objects=live_trips)
        result['meta'] = dict()
        return self.get_json_resp(result)

class Devices(ApiView): 
    """ Return list of devices """
    api_url = r'^devices/$'
    def get(self,request):
        import analysis.logic
        devices = analysis.logic.get_devices_summary()
        return self._prepare_list_resp(request,devices)

class DeviceReports(ApiView):
    """ Return reports for given device with id device_id
    <br>use <b>stops_only</b>=1 to get only stops
    <br>use <b>full</b>=1 to get also wifis
    """
    api_url = r'^devices/(?P<device_id>[\w ]+)/reports/'
    def get(self,request,device_id):
        import analysis.logic
        info = dict()
        info['since_id'] = int(request.GET.get('since_id',0))
        info['limit'] = int(request.GET.get('limit',200))
        info['offset'] = int(request.GET.get('offset',0))
        info['stops_only'] = bool(int(request.GET.get('stops_only',0)))
        info['bssid'] = request.GET.get('bssid')
        info['full'] = bool(int(request.GET.get('full',0)))
        reports = analysis.logic.get_device_reports(device_id,info)
        return self._prepare_list_resp(request,reports,info)

class DeviceStatus(ApiView):
    """ Returns the status of curret device, e.g. its real time location <br/>
    Should be used mainly for testing
    """
    api_url = r'^devices/(?P<device_id>[\w ]+)/status/'
    def get(self,request,device_id):
        import algorithm.train_tracker
        result = algorithm.train_tracker.get_device_status(device_id)
        return self.get_json_resp(result)

class BssidsToStopIds(ApiView):
    """ returns map of bssids to stops """
    api_url = r'^stops/bssids/'
    def get(self,request):
        import algorithm.bssid_tracker
        data = algorithm.bssid_tracker.get_bssid_data_for_app()
        return self.get_json_resp(data)

class AllStops(ApiView):
    """ return lists of stops with bssids
    """
    api_url = r'^stops/$'
    def get(self,request):
        from timetable.models import TtStop
        stops = TtStop.objects.all().order_by('gtfs_stop_id')
        import algorithm.bssid_tracker
        data = algorithm.bssid_tracker.get_bssids_by_stop_ids()
        content = [stop.to_json(bssids=data.get(stop.gtfs_stop_id,[])) for stop in stops]
        return self.get_json_resp(content)

class DistBetweenShapes(ApiView):
    api_url = r'^stops/distance/$'
    def get(self,request):
        import timetable.services
        if 'gtfs_stop_id1' not in request.GET or 'gtfs_stop_id2' not in request.GET:
            return HttpResponse(status=400,content='gtfs_stop_id1 and gtfs_stop_id2 are mandatory')
        content = timetable.services.find_distance_between_gtfs_stops_ids(request.GET['gtfs_stop_id1'],request.GET['gtfs_stop_id2'])
        return self.get_json_resp(content)

class BssidToStop(ApiView):
    """ Returns stop info for each bssid 
    get bssids as paramter
    """
    api_url = r'^analysis/bssid-info/'
    def get(self,request):
        bssids = self.GET.get('bssids').split(',')
        all = self.get_bool('all',False)
        pass


