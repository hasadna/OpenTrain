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
import timetable.services

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

def get_train_tracker_trip_delays_ids_list_of_lists_key(tracker_id):
    return "train_tracker:%s:trip_delays_ids_list_of_lists" % (tracker_id)

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

def add_report(report): 
    bssid_tracker.tracker.add(report)
    add_report_to_tracker(report.device_id, report)

def add_report_to_tracker(tracker_id, report):
    logger.info('Adding report to tracker_id "{}": {}'.format(tracker_id, report))
    day = set_tracker_day(tracker_id, report)
    
    # update train position
    if report.get_my_loc():
        update_coords(report, tracker_id)
    
    is_updated_stop_time = stop_detector.add_report(tracker_id, report)
    
    if is_updated_stop_time:
        logger.info('stop_time updated')
        stop_times = stop_detector.get_detected_stop_times(tracker_id)
        trip_delays_ids_list_of_lists = update_trips(tracker_id, day, stop_times)
        trip_ids = get_trusted_trips(trip_delays_ids_list_of_lists)
        for trip_id in trip_ids:
            trip_delays_ids_list = [x for x in trip_delays_ids_list_of_lists if x[0][1] == trip_id][0]
            if (len(stop_times)-1) in trip_delays_ids_list[0][2]:
                if len(trip_delays_ids_list[0][2]) == 2:  # Need to add the first station
                    if (len(stop_times)-2) in trip_delays_ids_list[0][2]:
                        stop_time = stop_times[trip_delays_ids_list[0][2][-2]]
                        logger.debug(stop_time)
                        save_stop_times_to_db(tracker_id, stop_time, trip_id) 
                    else:
                        logger.error('Two stops were detected for trip, last detected stop for tracker belongs to trip, but one before last does not, while it most probably should.')
                stop_time = stop_times[trip_delays_ids_list[0][2][-1]]
                logger.debug(stop_time)
                save_stop_times_to_db(tracker_id, stop_time, trip_id)

def save_stop_times_to_db(tracker_id, detected_stop_time, trip_id):
    logger.info('Saving stop_time to db. trip_id={}, stop_time={}'.format(trip_id, detected_stop_time))
    stop = timetable.services.get_stop(detected_stop_time.stop_id)
    departure_time = detected_stop_time.departure
    arrival_time = detected_stop_time.arrival
    from analysis.models import RtStop
    try:
        rs = RtStop.objects.get(tracker_id=tracker_id,stop=stop,trip__gtfs_trip_id=trip_id)
        logger.info('RtStop exists. Overriding.')
    except RtStop.DoesNotExist:
        rs = RtStop()
        logger.info('RtStop does not exist. Creating new one.')
    rs.tracker_id = tracker_id
    rs.trip = timetable.services.get_trip(trip_id)
    rs.stop = stop
    rs.act_arrival = arrival_time
    rs.act_departure = departure_time
    rs.save() 
    logger.info('RtStop saved: {}'.format(rs))  

def update_coords(report, tracker_id):
    loc = report.get_my_loc()
    coords = [loc.lat, loc.lon]
    logger.info('Updating coords for tracker_id={} by report={} to coords={}'.format(tracker_id, report, coords))    
    res_shape_sampled_point_ids, _ = shapes.all_shapes.query_sampled_points(coords, loc.accuracy_in_coords)
     
    added_count = cl.sadd(get_train_tracker_visited_shape_sampled_point_ids_key(tracker_id), res_shape_sampled_point_ids)

    trip_delays_ids_list_of_lists = load_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(tracker_id))
    trips = get_trusted_trips(trip_delays_ids_list_of_lists)

    for trip in trips:
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
    logger.info('Updating trips for tracker_id={}'.format(tracker_id))
    trip_delays_ids_list_of_lists = trip_matcher.get_matched_trips(tracker_id, detected_stop_times, day)
    logger.info('Updated trip_delays_ids_list_of_lists for tracker_id={}: {}'.format(tracker_id, trip_delays_ids_list_of_lists))
    save_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(tracker_id), trip_delays_ids_list_of_lists)
    return trip_delays_ids_list_of_lists

def get_trusted_trips(trip_delays_ids_list_of_lists):
    trip_ids = []
    if not trip_delays_ids_list_of_lists:
        return trip_ids
    for trip_delays_ids_list in trip_delays_ids_list_of_lists:
        trips = [x[1] for x in trip_delays_ids_list]
        time_deviation_in_seconds = [x[0] for x in trip_delays_ids_list]
        trip_id = get_trusted_trip_or_none(trips, time_deviation_in_seconds)
        if trip_id:
            trip_ids.append(trip_id)
    
    logger.info('Trusted trips={} for trip_delays_ids_list_of_lists={}'.format(trip_ids, trip_delays_ids_list_of_lists))
    return trip_ids

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
        logger.info('time_deviation_ratio={} and so we trust trip={}'.format(time_deviation_ratio, trips[0]))
        return trips[0] 
    else:
        logger.info('time_deviation_ratio={} and so we do not trust trip={}'.format(time_deviation_ratio, trips[0]))
        return None 

def get_device_status(device_id):
    trip_delays_ids_list_of_lists = load_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(device_id))
    return trip_delays_ids_list_of_lists

def get_device_status_for_app(device_id):
    trip_delays_ids_list_of_lists = load_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(device_id))
    return get_trusted_trips(trip_delays_ids_list_of_lists)

cl = get_redis_client()
p = get_redis_pipeline()
