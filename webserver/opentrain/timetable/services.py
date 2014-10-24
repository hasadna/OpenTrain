import models
import common.ot_utils
import json
from django.conf import settings
from django.utils.translation import ugettext as _
from timetable.models import TtStopTime,TtStop,TtTrip

def get_stations():
    result = models.TtStop.objects.all().order_by('stop_name',)
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
   
 
def find_distance_between_gtfs_stops_ids(gtfs_stop_id1,gtfs_stop_id2):
    stop1 = TtStop.objects.get(gtfs_stop_id=gtfs_stop_id1)
    stop2 = TtStop.objects.get(gtfs_stop_id=gtfs_stop_id2)
    return find_distance_between_stops(stop1,stop2)

MIN_DIST = 100

class ShapeDist(object):
    def __init__(self,shape,**kwargs):
        self.shape = shape
        for k,v in kwargs.iteritems():
            setattr(self,k,v)
        self.distance = self.compute_distance()
        self.shape_diff = abs(self.idx1-self.idx2)

    def compute_distance(self):
        result = 0
        points = self.shape.get_points_array()
        min_idx = min(self.idx1,self.idx2)
        max_idx = max(self.idx1,self.idx2)
        last_point = points[min_idx]
        result = 0.0
        for point in points[min_idx+1:max_idx+1]:
            result += common.ot_utils.latlon_to_meters(last_point[0],last_point[1],point[0],point[1])
            last_point=point
        return result

def find_min_dist_to(shape,stop):
    import redis_intf.client
    cl = redis_intf.client.get_redis_client()
    redis_key = 'min_dist_{0}_{1}'.format(shape.id,stop.id)
    val = cl.get(redis_key)
    if val:
        return json.loads(val)
    latlon = stop.stop_lat,stop.stop_lon
    points = shape.get_points_array()
    dists = [(common.ot_utils.latlon_to_meters(point[0],point[1],latlon[0],latlon[1]),idx) for idx,point in enumerate(points)]
    result = min(dists)
    cl.setex(redis_key,600,json.dumps(result))
    return result

def find_distance_between_stops(istop1,istop2):
    if istop1.gtfs_stop_id < istop2.gtfs_stop_id:
        stop1 = istop1
        stop2 = istop2
    else:
        stop1 = istop2
        stop2 = istop1
    shapes1 = set(TtStopTime.objects.filter(stop__id=stop1.id).values_list('trip__shape__id',flat=True).distinct())
    shapes2 = set(TtStopTime.objects.filter(stop__id=stop2.id).values_list('trip__shape__id',flat=True).distinct())
    common_shapes = shapes1 & shapes2
    if not common_shapes:
        return None
    shapes = models.TtShape.objects.filter(id__in=common_shapes)
    relevant_shapes = []
    for shape in shapes:
        min_dist1,min_idx1 = find_min_dist_to(shape,stop1)
        min_dist2,min_idx2 = find_min_dist_to(shape,stop2)
        if min_dist1 < MIN_DIST and min_dist2 < MIN_DIST:
            relevant_shapes.append(ShapeDist(shape=shape,idx1=min_idx1,idx2=min_idx2))
    dists = []
    for rs in relevant_shapes:
        dists.append({
                       'shape_id' : rs.shape.id,
                       'points_delta' : rs.shape_diff,
                       'distance' : rs.distance,
                       'aerial_distance' : common.ot_utils.latlon_to_meters(stop1.stop_lat,
                                                                     stop1.stop_lon,
                                                                     stop2.stop_lat,
                                                                     stop2.stop_lon)})
    dists.sort(key=lambda x : x['distance'])
    uniq_dists = []
    if dists:
        uniq_dists.append(dists[0])
    for dist in dists:
        if abs(dist['distance'] - uniq_dists[-1]['distance']) > 10:
            uniq_dists.append(dist)

    result = {'gtfs_stop_id1': stop1.gtfs_stop_id,
              'gtfs_stop_id2': stop2.gtfs_stop_id,
              'dists' : uniq_dists}
    return result

def get_dists_matrix(force=False):
    cache_key = 'final_dists'
    import redis_intf.client
    cl = redis_intf.client.get_redis_client()
    val = cl.get(cache_key)
    if not force and val:
        return json.loads(val)
    stops = list(TtStop.objects.all().order_by('gtfs_stop_id'))
    result = []
    for idx1,stop1 in enumerate(stops):
        print idx1
        for idx2,stop2 in enumerate(stops):
            if stop1.gtfs_stop_id < stop2.gtfs_stop_id:
                dist_entry = find_distance_between_stops(stop1,stop2)
                if dist_entry is not None:
                    result.append(dist_entry)
    cl.set(cache_key,json.dumps(result))
    return result

def check_dists():
    matrix = get_dists_matrix()
    for entry in matrix:
        dists = entry['dists']
        if not dists:
            continue
        min_dist = min(d['distance'] for d in dists)
        max_dist = max(d['distance'] for d in dists)
        if abs(max_dist-min_dist) > 10:
            print entry['gtfs_stop_id1'],entry['gtfs_stop_id2'],min_dist,max_dist

def create_dists_csv():
    import csv
    import os.path
    matrix = get_dists_matrix()
    with open(os.path.join(settings.BASE_DIR,'timetable/static/timetable/dists.csv'),'w') as fh:
        writer = csv.writer(fh)
        writer.writerow(['stop_id1','stop_name1','stop_id2','stop_name2','num_results','distance1','aerial_distance1','distance2','aerial_distance2'])
        for entry in matrix:
            stop1 = TtStop.objects.get(gtfs_stop_id=entry['gtfs_stop_id1'])
            stop2 = TtStop.objects.get(gtfs_stop_id=entry['gtfs_stop_id2'])
            dists = entry['dists']
            d0 = dists[0] if len(dists) >= 1 else None
            d1 = dists[1] if len(dists) >= 2 else None
            writer.writerow([stop1.gtfs_stop_id,
                             stop1.get_short_name(),
                             stop2.gtfs_stop_id,
                             stop2.get_short_name(),
                             len(dists),
                             int(d0['distance']) if d0 else '',
                             int(d0['aerial_distance']) if d0 else '',
                             int(d1['distance']) if d1 else '',
                             int(d1['aerial_distance']) if d1 else ''])
