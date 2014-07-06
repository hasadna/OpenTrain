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

def get_expected_location(trip,dt):
    from models import ShapeJson
    normal_time = common.ot_utils.get_normal_time(dt)
    stop_times = list(trip.stoptime_set.all())
    stop_times.sort(key=lambda x : x.stop_sequence)
    before_stop_list = [st for st in stop_times if st.departure_time <= normal_time]
    after_stop_list = [st for st in stop_times if st.arrival_time >= normal_time]
    before_stop = before_stop_list[-1] if before_stop_list else None
    after_stop = after_stop_list[0] if after_stop_list else None
    # if there is no before stop, means that the train is not in the first stop
    # so we just return the after stop
    # if no after stop - the reverse
    if not before_stop:
        return ([after_stop.stop.stop_lat,after_stop.stop.stop_lon],[after_stop.stop.stop_lat,after_stop.stop.stop_lon])
    if not after_stop or after_stop == before_stop:
        return ([before_stop.stop.stop_lat,before_stop.stop.stop_lon],[before_stop.stop.stop_lat,before_stop.stop.stop_lon])
    points = json.loads(ShapeJson.objects.get(shape_id=trip.shape_id).points)
    idx_before = find_closest_point_index(trip,points,lat=before_stop.stop.stop_lat,lon=before_stop.stop.stop_lon)
    idx_after = find_closest_point_index(trip,points,lat=after_stop.stop.stop_lat,lon=after_stop.stop.stop_lon)
    delta = float(after_stop.arrival_time - before_stop.departure_time)
    if delta == 0:
        relative = 0
    else:
        relative = (normal_time - before_stop.departure_time) / delta
    num_points = idx_after - idx_before
    idx_result = int(relative*num_points) +  idx_before
    result = points[idx_result]
    fake_result = None
    to_fake = fake_cur_location(trip) 
    if to_fake:
        pt_delta = (int() -5 )*10;
        if pt_delta == 0:
            pt_delta = 1
        idx_fake_result = idx_result + pt_delta
        if idx_fake_result < 0:
            idx_fake_result = 0
        if idx_fake_result >= len(points):
            idx_fake_result = points[-1]
        fake_result = points[idx_fake_result]
    return (result,fake_result)
    

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
    

def fake_cur_location(trip):
    last_digit = int(trip.trip_id[-1])
    if settings.FAKE_CUR and last_digit % 2 == 0: 
        return True
    return False

