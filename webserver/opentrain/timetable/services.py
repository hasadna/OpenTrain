import models
import common.ot_utils
import json
from django.conf import settings
from django.utils.translation import ugettext as _
from timetable.models import TtStopTime,TtStop,TtTrip

def get_stations():
    result = models.TtStop.objects.all().order_by('stop_name')
    return list(result)

def get_trip(trip_id):
    return TtTrip.objects.get(gtfs_trip_id=trip_id)

def get_trips(trip_ids):
    return TtTrip.objects.filter(gtfs_trip_id__in=trip_ids)

def get_stations_choices():
    stations = get_stations()
    result = []
    for station in stations:
        result.append((unicode(station.gtfs_stop_id),_(station.stop_name)))
    result.sort(key=lambda x : x[1])
    return tuple(result)
        
def get_all_trips_in_datetime(dt):
    return TtTrip.objects.filter(from_stoptime__exp_departure__lte=dt).filter(to_stoptime__exp_arrival__gte=dt)

def get_all_trips_in_date(date):
    return TtTrip.objects.filter(date=date)

def get_trips_by_day(day):
    return get_all_trips_in_date(day)

def get_expected_location(trip,dt):
    assert isinstance(trip,TtTrip)
    stop_times = list(trip.get_stop_times())
    before_stop_list = [st for st in stop_times if st.exp_departure <= dt]
    after_stop_list = [st for st in stop_times if st.exp_arrival >= dt]
    before_stop = before_stop_list[-1] if before_stop_list else None
    after_stop = after_stop_list[0] if after_stop_list else None
    # if there is no before stop, means that the train is not in the first stop
    # so we just return the after stop
    # if no after stop - the reverse
    if not before_stop:
        return ([after_stop.stop.stop_lat,after_stop.stop.stop_lon],[after_stop.stop.stop_lat,after_stop.stop.stop_lon])
    if not after_stop or after_stop == before_stop:
        return ([before_stop.stop.stop_lat,before_stop.stop.stop_lon],[before_stop.stop.stop_lat,before_stop.stop.stop_lon])
    points = trip.get_points()
    idx_before = find_closest_point_index(trip,points,lat=before_stop.stop.stop_lat,lon=before_stop.stop.stop_lon)
    idx_after = find_closest_point_index(trip,points,lat=after_stop.stop.stop_lat,lon=after_stop.stop.stop_lon)
    delta = (after_stop.exp_arrival - before_stop.exp_departure).total_seconds()
    if delta == 0:
        relative = 0
    else:
        relative = (dt - before_stop.exp_departure).total_seconds() / delta
    num_points = idx_after - idx_before
    idx_result = int(relative*num_points) +  idx_before
    result = points[idx_result]
    return result
    

def find_closest_point_index(trip,points,lat,lon):
    def dist(pt):
        return (pt[0]-lat)*(pt[0]-lat) + (pt[1]-lon)*(pt[1]-lon)
    return min(enumerate(points),key = lambda t : dist(t[1]))[0]
    
def do_search(in_station=None,when=None,before=None,after=None):
    import datetime
    before = int(before or 0)
    after = int(after or 0)
    start_time = when - datetime.timedelta(minutes=before)
    end_time = when + datetime.timedelta(minutes=after)
    return do_search_in(in_station,start_time,end_time)

def do_search_in(in_station,start_time,end_time):
    stop = TtStop.objects.get(gtfs_stop_id=in_station)
    stop_times_in_station = TtStopTime.objects.filter(stop=stop)
    stops_in_time = stop_times_in_station.filter(exp_arrival__gte=start_time,exp_arrival__lte=end_time)
    return stops_in_time
    
def get_all_days():
    dates = models.TtTrip.objects.all().values_list('date',flat=True).distinct()
    return [common.ot_utils.get_localtime(x) for x in dates]

    
def get_shape_coords_by_trip(trip):
    assert False,'Use trip.get_points()'
    
def get_trip_stop_times(trip):
    assert False,'Use trip.get_stop_times'
    
    
def get_all_shapes():
    all_shapes = list(models.TtShape.objects.all())
    return all_shapes

def get_all_stops_ordered_by_id():
    return models.TtStop.objects.all().order_by('gtfs_stop_id')

def print_trip_stop_times(trip_id):
    trip = get_trip(trip_id)
    print('')
    trip.print_stoptimes()
    print('')
   
def get_stop(gtfs_stop_id):
    return TtStop.objects.get(gtfs_stop_id=gtfs_stop_id)
   
 
    
