import timetable.services
import os
import config
import numpy as np
import stops
import shapes
from pprint import pprint
from utils import *
from common.ot_utils import *
from common import ot_utils
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import datetime
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import json
from stop_detector import DetectedStopTime
from ot_profiler import do_profile
from gtfs_datastore import TripDatastore

all_stops = stops.all_stops
    
# None means we cannot find a reasonable trip list
# empty list means there are no trips that fit this tracker
#@do_profile(follow=[])
def get_matched_trips(tracker_id, detected_stop_times, day):
    if len(detected_stop_times) == 0:
        return None
    detected_stop_ids = [x.stop_id for x in detected_stop_times]   
    trip_datastore = TripDatastore(day)
    costops = trip_datastore.costop_matrix # beseder
    
    stop_ids = [x.stop_id for x in detected_stop_times]
    stop_ids_inds = [all_stops.id_list.index(x) for x in stop_ids]

    trips_with_visited_stops = trip_datastore.GetTripsByStops(stop_ids_inds) # beseder
    
    trip_in_right_direction = []
    arrival_delta_abs_means_seconds = []
    trips_filtered_by_stop_order = []
    trips_filtered_by_stop_order_detected_stop_inds = []
    for i, t in enumerate(trips_with_visited_stops):
        stops_dict = trip_datastore.trip_datastore[t]['stops']

        start_time = trip_datastore.trip_datastore[t]['start_time']
        end_time = trip_datastore.trip_datastore[t]['end_time']

        detected_stop_times_in_time_range = []
        for i, x in enumerate(detected_stop_times):
            arrival = x.arrival
            if start_time <= arrival and arrival <= end_time:
                detected_stop_times_in_time_range.append(x)
        filtered_detected_stop_times_stop_inds = [all_stops.id_list.index(x.stop_id) for x in detected_stop_times_in_time_range]
        impossible_stops_inds = trip_datastore.GetImpossibleCostops(filtered_detected_stop_times_stop_inds) # beseder
        impossible_stops_ids = [all_stops.id_list[x] for x in impossible_stops_inds]
        has_impossible_stops = bool([x for x in impossible_stops_ids if x in stops_dict])
        if has_impossible_stops:
            continue

        trip_stop_tuples = []
        filtered_detected_stop_times = []
        filtered_detected_stop_times_inds = []
        for i, x in enumerate(detected_stop_times):
            # if checks for:
            # - stops that are detected and are in trip:
            # - stops that are in trip time range:
            arrival = x.arrival
            if x.stop_id in stops_dict and start_time <= arrival and arrival <= end_time:
                trip_stop_tuples.append(stops_dict[x.stop_id])
                filtered_detected_stop_times.append(x)
                filtered_detected_stop_times_inds.append(i)
        # filter by stop order and at least two detected stops:    
        #4900 Tel Aviv HaHagana
        #3600 Tel Aviv - University
        #3700 Tel Aviv Center - Savidor
        #4600 Tel Aviv HaShalom        
        has_tel_aviv_stop = bool([x for x in filtered_detected_stop_times if x.stop_id in [4900, 3600, 3700, 4600]])
        non_tel_aviv_stops = len([x for x in filtered_detected_stop_times if x.stop_id not in [4900, 3600, 3700, 4600]])
        stop_count_with_tel_aviv_as_one_stop = non_tel_aviv_stops + int(has_tel_aviv_stop)
        if stop_count_with_tel_aviv_as_one_stop >= 2:
            gtfs_sequence_of_detected_stops = [x[0] for x in trip_stop_tuples]
            if is_increasing(gtfs_sequence_of_detected_stops):
                trips_filtered_by_stop_order.append(t)
                trips_filtered_by_stop_order_detected_stop_inds.append(filtered_detected_stop_times_inds)
                # calc deviation from gtfs arrival time:
                arrival_delta_abs_sum = 0
                for detected_stop_time in filtered_detected_stop_times:
                    stop_and_arrival_gtfs = stops_dict.get(detected_stop_time.stop_id)
                    if stop_and_arrival_gtfs:
                        arrival_delta_seconds = stop_and_arrival_gtfs[1] - detected_stop_time.arrival
                        arrival_delta_abs_sum += abs(arrival_delta_seconds).total_seconds()
                arrival_delta_abs_mean = arrival_delta_abs_sum/len(filtered_detected_stop_times_inds)
                arrival_delta_abs_means_seconds.append(arrival_delta_abs_mean)                
    
    trip_delays_ids = sorted(zip(arrival_delta_abs_means_seconds, trips_filtered_by_stop_order, trips_filtered_by_stop_order_detected_stop_inds))
    
    trip_delays_ids_temp = trip_delays_ids
    trip_delays_ids_list_of_lists = []
    while len(trip_delays_ids_temp) > 0:
        trip_delay_id_root = trip_delays_ids_temp[0]
        del trip_delays_ids_temp[0]
        trip_delays_ids_list = [trip_delay_id_root]
        intersecting_trip_delays_ids = [x for x in trip_delays_ids_temp if trip_datastore.DoTripsIntersect(trip_delay_id_root[1], x[1])]
        trip_delays_ids_list += intersecting_trip_delays_ids
        trip_delays_ids_list_of_lists.append(trip_delays_ids_list)
        trip_delays_ids_temp = [x for x in trip_delays_ids_temp if x not in intersecting_trip_delays_ids]
    print trip_delays_ids_list_of_lists
    return trip_delays_ids_list_of_lists

cl = get_redis_client()
p = get_redis_pipeline()