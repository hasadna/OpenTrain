import gtfs.models
from scipy import spatial
import os
import config
import numpy as np
import copy
import stops
import shapes
from sklearn.hmm import MultinomialHMM
from utils import *
from common.ot_utils import *
from collections import deque
from common import ot_utils
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import datetime
import bssid_tracker 
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import json
from utils import enum
from redis import WatchError
import stop_detector
import trip_matcher

# Trip edge (a,b): trip a must end before trip b starts
# They may share at most one station

# Discovered stops may not be a scheduled stop, so trip might not stop at all
# stops, but they must all be on its general route. For example, the Rehovot
# to Tel Aviv train may not stop at Be'er Yaakov, but Be'er Yaakov must be on
# the general route between Rehovot and Tel-Aviv.


TRACKER_TTL = 1 * 60
TRACKER_REPORT_FOR_TRIP_COUNT_LOWER_THAN = 3


# what is this used for?
def get_train_tracker_visited_shape_sampled_point_ids_key(tracker_id):
    return "train_tracker:%s:visited_shape_sampled_point_ids" % (tracker_id)   

# Save report's day. We may have to think about what happens after midnight and maybe stay with the previous day because that's how the GTFS works
def get_train_tracker_day(tracker_id):
    return "train_tracker:%s:day" % (tracker_id)

# relevant_services = services for today. used to filter trips by day
def get_train_tracker_relevant_services_key(tracker_id):
    return "train_tracker:%s:relevant_services" % (tracker_id)

def get_train_tracker_coords_key(tracker_id):
    return "train_tracker:%s:coords" % (tracker_id)

def get_train_tracker_trip_ids_deviation_seconds_key(tracker_id):
    return "train_tracker:%s:trip_ids_deviation_seconds" % (tracker_id)

def get_train_tracker_trip_ids_key(tracker_id):
    return "train_tracker:%s:trip_ids" % (tracker_id)

def get_current_trip_id_coords_key(trip_id):
    return 'current_trip_id:coords:%s' % (trip_id)

def get_current_trip_id_coords_timestamp_key(trip_id):
    return 'current_trip_id:coords_timestamp:%s' % (trip_id)

def get_current_trip_id_report_timestamp_key(trip_id):
    return 'current_trip_id:report_timestamp:%s' % (trip_id)

def set_tracker_day(tracker_id, report):
    day_str = report.timestamp.strftime("%Y-%m-%d")
    save_by_key(get_train_tracker_day(tracker_id), day_str, cl=p)

def get_relevant_service_ids(tracker_id):
    result = load_by_key(get_train_tracker_relevant_services_key(tracker_id))
    if not result:
        start_date = load_by_key(get_train_tracker_day(tracker_id))
        relevant_services = gtfs.models.Service.objects.filter(start_date \
                                                               = start_date)
        result = [x[0] for x in relevant_services.all().values_list(\
            'service_id')]
        save_by_key(get_train_tracker_relevant_services_key(tracker_id),\
                    result)    
    return result

def add_report_to_tracker(tracker_id, report):
    set_tracker_day(tracker_id, report)
    
    # update train position
    if report.get_my_loc():
        try_update_coords(report, tracker_id)
    
    stop_times, stops_have_changed = stop_detector.add_report(tracker_id,\
                                                              report)
    
    if stops_have_changed:
        update_trips(tracker_id, stop_times)
        # send last stop_time from stop_times
        #save_stop_times_to_db(tracker_id, arrival_unix_timestamp, 
        #                     stop_id_and_departure_time)

def save_stop_times_to_db(tracker_id, arrival_unix_timestamp, stop_id_and_departure_time):
    stop_id, departure_unix_timestamp = stop_id_and_departure_time.split('_')
    name = stops.all_stops[stop_id].name
    departure_time = ot_utils.unix_time_to_localtime(int(departure_unix_timestamp)) if departure_unix_timestamp else None 
    arrival_time = ot_utils.unix_time_to_localtime(int(arrival_unix_timestamp))
    stop_time = DetectedStopTime(stop_id, arrival_time, departure_time)
    print stop_time
    trips, time_deviation_in_seconds = get_possible_trips(tracker_id)
    if len(time_deviation_in_seconds) > 1:
        time_deviation_ratio = time_deviation_in_seconds[0]/time_deviation_in_seconds[1] 
    else:
        time_deviation_ratio = 0;
    if len(trips) > 0 and len(trips) <= 3 and time_deviation_ratio < 0.5:
        trip_id = trips[0]
        from analysis.models import RealTimeStop
        try:
            rs = RealTimeStop.objects.get(tracker_id=tracker_id,stop_id=stop_id,trip_id=trip_id)
        except RealTimeStop.DoesNotExist:
            rs = RealTimeStop()
        rs.tracker_id = tracker_id
        rs.trip_id = trip_id
        rs.stop_id = stop_id
        rs.arrival_time = arrival_time
        rs.departure_time = departure_time
        rs.save()    

def try_update_coords(report, tracker_id):
    loc = report.get_my_loc()
    coords = [loc.lat, loc.lon]
    res_shape_sampled_point_ids, _ = shapes.all_shapes.query_sampled_points(coords, loc.accuracy_in_coords)
     
    added_count = cl.sadd(get_train_tracker_visited_shape_sampled_point_ids_key(tracker_id), res_shape_sampled_point_ids)

    trips = load_by_key(get_train_tracker_trip_ids_key(tracker_id))
    trip = trips[0] if trips else None
    if added_count > 0:
        
        save_by_key(get_train_tracker_coords_key(tracker_id), coords, cl=p)
        
        if trip is not None and len(trips) <= TRACKER_REPORT_FOR_TRIP_COUNT_LOWER_THAN:
            save_by_key(get_current_trip_id_coords_key(trip), coords, timeout=TRACKER_TTL, cl=p)
            save_by_key(get_current_trip_id_coords_timestamp_key(trip), ot_utils.dt_time_to_unix_time(report.timestamp), timeout=TRACKER_TTL, cl=p)
        p.execute()              
    
    if trip is not None:    
        cl.setex(get_current_trip_id_report_timestamp_key(trip), TRACKER_TTL, ot_utils.dt_time_to_unix_time(report.timestamp))

def update_trips(tracker_id, detected_stop_times):
    relevant_service_ids = get_relevant_service_ids(tracker_id)
    trips, time_deviation_in_seconds = trip_matcher.get_possible_trips(tracker_id, detected_stop_times, relevant_service_ids)
    #if len(trips) <= 100:
    save_by_key(get_train_tracker_trip_ids_key(tracker_id), trips)
    save_by_key(get_train_tracker_trip_ids_deviation_seconds_key(tracker_id), time_deviation_in_seconds)
        
def print_possible_trips(tracker_id):
    trips, arrival_delta_abs_sums_seconds = get_possible_trips(tracker_id)
    print 'Trip count = %d' %(len(trips))
    for t in trips:
        trip_stop_times = gtfs.models.StopTime.objects.filter(trip = t).order_by('arrival_time')
        print "trip id: %s" % (t)
        for x in trip_stop_times:
            print db_time_to_datetime(x.arrival_time), db_time_to_datetime(x.departure_time), x.stop
        print        

def get_possible_trips(tracker_id):
    trips = load_by_key(get_train_tracker_trip_ids_key(tracker_id))
    time_deviation_in_seconds = load_by_key(get_train_tracker_trip_ids_deviation_seconds_key(tracker_id))    
    return trips, time_deviation_in_seconds

def add_report(report):  
    bssid_tracker.tracker.add(report)
    add_report_to_tracker(report.device_id, report)

cl = get_redis_client()
p = get_redis_pipeline()
