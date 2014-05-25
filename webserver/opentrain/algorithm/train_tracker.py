import gtfs.models
import os
import config
import numpy as np
import stops
import shapes
from utils import *
from common.ot_utils import *
from common import ot_utils
from alg_logger import logger
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
import stop_detector
import trip_matcher

# Trip edge (a,b): trip a must end before trip b starts
# They may share at most one station

# Discovered stops may not be a scheduled stop, so trip might not stop at all
# stops, but they must all be on its general route. For example, the Rehovot
# to Tel Aviv train may not stop at Be'er Yaakov, but Be'er Yaakov must be on
# the general route between Rehovot and Tel-Aviv.


TRACKER_TTL = 1 * 60

# this field saves visited shape points so our location estimatewe don't jitter back and forth when reports are inaccurate or not processed in order
def get_train_tracker_visited_shape_sampled_point_ids_key(tracker_id):
    return "train_tracker:%s:visited_shape_sampled_point_ids" % (tracker_id)   

# Save report's day. We may have to think about what happens after midnight and maybe stay with the previous day because that's how the GTFS works
def get_train_tracker_day_key(tracker_id):
    return "train_tracker:%s:day" % (tracker_id)

# relevant_services = services for today. used to filter trips by day
def get_train_tracker_relevant_services_key(tracker_id):
    return "train_tracker:%s:relevant_services" % (tracker_id)

def get_train_tracker_trip_ids_deviation_seconds_key(tracker_id):
    return "train_tracker:%s:trip_ids_deviation_seconds" % (tracker_id)

def get_train_tracker_trip_ids_key(tracker_id):
    return "train_tracker:%s:trip_ids" % (tracker_id)

def get_current_trip_id_coords_key(trip_id):
    return 'current_trip_id:coords:%s' % (trip_id)

# last report timestamp for which coords was updated
def get_current_trip_id_coords_timestamp_key(trip_id):
    return 'current_trip_id:coords_timestamp:%s' % (trip_id)

# last report timestamp for which coords was observed. If the train is standing still and reports are coming in, this field will continue to update while the coords_timestamp_key field will not
def get_current_trip_id_report_timestamp_key(trip_id):
    return 'current_trip_id:report_timestamp:%s' % (trip_id)

def set_tracker_day(tracker_id, report):
    day_str = report.timestamp.strftime("%Y-%m-%d")
    save_by_key(get_train_tracker_day_key(tracker_id), day_str, cl=p)
    return report.timestamp.date()

def get_relevant_service_ids(tracker_id):
    result = load_by_key(get_train_tracker_relevant_services_key(tracker_id))
    if not result:
        start_date = load_by_key(get_train_tracker_day_key(tracker_id))
        relevant_services = gtfs.models.Service.objects.filter(start_date \
                                                               = start_date)
        result = [x[0] for x in relevant_services.all().values_list(\
            'service_id')]
        save_by_key(get_train_tracker_relevant_services_key(tracker_id),\
                    result)    
    return result

def add_report(report):  
    bssid_tracker.tracker.add(report)
    add_report_to_tracker(report.device_id, report)

def add_report_to_tracker(tracker_id, report):
    day = set_tracker_day(tracker_id, report)
    
    # update train position
    if report.get_my_loc():
        update_coords(report, tracker_id)
    
    stop_times, is_stops_updated = stop_detector.add_report(tracker_id,\
                                                              report)
    
    if is_stops_updated:
        trips, time_deviation_in_seconds = update_trips(tracker_id, day, stop_times)
        if len(stop_times) == 2:  # Need to add the first station
            logger.debug(stop_times[-2])
            save_stop_times_to_db(tracker_id, stop_times[-2], trips,\
                                  time_deviation_in_seconds)        
        logger.debug(stop_times[-1])
        save_stop_times_to_db(tracker_id, stop_times[-1], trips,\
                              time_deviation_in_seconds)

def save_stop_times_to_db(tracker_id, detected_stop_time, trips,\
                          time_deviation_in_seconds):
    stop_id = detected_stop_time.stop_id
    departure_time = detected_stop_time.departure
    arrival_time = detected_stop_time.arrival
    trip_id = get_trusted_trip_or_none(trips, time_deviation_in_seconds)
    if trip_id:
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
        logger.debug(str(rs))  

def update_coords(report, tracker_id):
    loc = report.get_my_loc()
    coords = [loc.lat, loc.lon]
    res_shape_sampled_point_ids, _ = shapes.all_shapes.query_sampled_points(coords, loc.accuracy_in_coords)
     
    added_count = cl.sadd(get_train_tracker_visited_shape_sampled_point_ids_key(tracker_id), res_shape_sampled_point_ids)

    trips, time_deviation_in_seconds = get_trips(tracker_id)
    trip = get_trusted_trip_or_none(trips, time_deviation_in_seconds)

    if trip:
        cl.setex(get_current_trip_id_report_timestamp_key(trip), TRACKER_TTL, ot_utils.dt_time_to_unix_time(report.timestamp))
        if added_count > 0:
            save_by_key(get_current_trip_id_coords_key(trip),\
                        coords,\
                        timeout=TRACKER_TTL, cl=p)
            save_by_key(get_current_trip_id_coords_timestamp_key(trip),\
                        ot_utils.dt_time_to_unix_time(report.timestamp),\
                        timeout=TRACKER_TTL, cl=p)
        else: # extend expiration:
            p.expire(get_current_trip_id_coords_key(trip), TRACKER_TTL)
            p.expire(get_current_trip_id_coords_timestamp_key(trip), TRACKER_TTL)
        p.execute()          

def update_trips(tracker_id, day, detected_stop_times):
    relevant_service_ids = get_relevant_service_ids(tracker_id)
    trips, time_deviation_in_seconds = trip_matcher.get_matched_trips(tracker_id, detected_stop_times, relevant_service_ids, day)
    save_by_key(get_train_tracker_trip_ids_key(tracker_id), trips)
    save_by_key(get_train_tracker_trip_ids_deviation_seconds_key(tracker_id), time_deviation_in_seconds)
    return trips, time_deviation_in_seconds
        
def get_trips(tracker_id):
    trips = load_by_key(get_train_tracker_trip_ids_key(tracker_id))
    time_deviation_in_seconds = load_by_key(get_train_tracker_trip_ids_deviation_seconds_key(tracker_id))    
    return trips, time_deviation_in_seconds

def print_trips(tracker_id):
    trips, arrival_delta_abs_sums_seconds = get_trips(tracker_id)
    print 'Trip count = %d' %(len(trips))
    for trip in trips:
        print "trip id: %s" % (trip)        
        trip_stop_times = gtfs.models.StopTime.objects.filter(trip = trip).order_by('arrival_time')
        for x in trip_stop_times:
            print db_time_to_datetime(x.arrival_time), db_time_to_datetime(x.departure_time), x.stop
        print

def get_trusted_trip_or_none(trips, time_deviation_in_seconds):
    # some heuristics to evaluate if we already have a trip we trust
    # enough to save it in db:
    if not trips:
        return None
    if len(time_deviation_in_seconds) > 1:
        time_deviation_ratio = time_deviation_in_seconds[0]/time_deviation_in_seconds[1] 
    else:
        time_deviation_ratio = 0;
    do_trust_trip = len(trips) > 0 and time_deviation_ratio < 0.5
    if do_trust_trip:
        return trips[0] 
    else:
        return None 

cl = get_redis_client()
p = get_redis_pipeline()
