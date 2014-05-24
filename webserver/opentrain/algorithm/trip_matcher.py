import gtfs.models
import os
import config
import numpy as np
import stops
import shapes
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
def get_matched_trips(tracker_id, detected_stop_times,\
                       relevant_service_ids, day, print_debug_info=True):
    if len(detected_stop_times) == 0:
        return None, None
    trip_datastore = TripDatastore(day)
    costops = trip_datastore.costop_matrix
    
    stop_ids = [x.stop_id for x in detected_stop_times]
    stop_ids_inds = [all_stops.id_list.index(x) for x in stop_ids]
    # we multiply AND rows so that any 0 will invalidate the stop - all stops
    # need to agree that this is a legal stop
    possible_costops_inds = (costops[stop_ids_inds,:].sum(axis=0) == len(stop_ids_inds)).astype(int)
    possible_costops_inds = possible_costops_inds.ravel().nonzero()[0]
    possible_costops_ids = [all_stops.id_list[x] for x in possible_costops_inds]
    impossible_costops_ids = [x for x in all_stops if x not in possible_costops_ids]
    impossible_costops_ind_ids = [all_stops.id_list.index(x) for x in impossible_costops_ids]
    
    trips_with_visited_stops = trip_datastore.trip_stop_matrix[:,stop_ids_inds]
    trips_with_visited_stops = (trips_with_visited_stops == 1).astype(int)
    trips_with_visited_stops = trips_with_visited_stops.sum(axis=1).nonzero()[0]
    inv_map = {v:k for k, v in trip_datastore.trip_stop_matrix_trip_ids_inds.items()}
    trips_with_visited_stops = [inv_map[x] for x in trips_with_visited_stops]

    trips_with_visited_stops_inds = [trip_datastore.trip_stop_matrix_trip_ids_inds[x] for x in trips_with_visited_stops]
    trips_with_impossible_stops = (trip_datastore.trip_stop_matrix[trips_with_visited_stops_inds,:][:,impossible_costops_ind_ids] == 1).astype(int)
    trips_with_impossible_stops = trips_with_impossible_stops.sum(axis=1).nonzero()[0]
    trips_with_impossible_stops = [trips_with_visited_stops[x] for x in trips_with_impossible_stops]
    trips_with_visited_stops_filtered_by_costops = list(set(trips_with_visited_stops) - set(trips_with_impossible_stops))

    # filter by stop existence and its time frame:
    trips_filtered_by_stops_and_times = trips_with_visited_stops_filtered_by_costops
    # filter by stop order and at least two detected stops:
    trip_in_right_direction = []
    for i, t in enumerate(trips_filtered_by_stops_and_times):
        detected_stop_ids = [x.stop_id for x in detected_stop_times]   
        stops = trip_datastore.trip_datastore[t]['stops']
        trip_stop_times = [stops[x] for x in detected_stop_ids if x in stops]
        if len(trip_stop_times) >= 2:
            gtfs_arrival_of_detected_stops = [x[0] for x in trip_stop_times]
            if is_increasing(gtfs_arrival_of_detected_stops):
                trip_in_right_direction.append(i)
    
    trips_filtered_by_stops_and_times = [trips_filtered_by_stops_and_times[i] for i in trip_in_right_direction]
    
    arrival_delta_abs_sums_seconds = []
    #departure_delta_abs_sums = []
    for t in trips_filtered_by_stops_and_times:
        stop_times_gtfs = trip_datastore.trip_datastore[t]['stops']
        arrival_delta_abs_sum = 0
        #departure_delta_abs_sum = 0
        for detected_stop_time in detected_stop_times:
            stop_and_arrival_gtfs = stop_times_gtfs.get(detected_stop_time.stop_id)
            if stop_and_arrival_gtfs:
                arrival_delta_seconds = stop_and_arrival_gtfs[1] - datetime_to_db_time(detected_stop_time.arrival)
                #departure_delta_seconds = stop_time[2] - datetime_to_db_time(tracked_stop_time.departure)
                arrival_delta_abs_sum += abs(arrival_delta_seconds)
                #departure_delta_abs_sum += abs(departure_delta_seconds)
        arrival_delta_abs_sums_seconds.append(arrival_delta_abs_sum)
        #departure_delta_abs_sums.append(departure_delta_abs_sum)
    
    # sort results by increasing arrival time 
    sorted_trips = sorted(zip(arrival_delta_abs_sums_seconds,trips_filtered_by_stops_and_times))
    trips_filtered_by_stops_and_times = [x for (y,x) in sorted_trips]
    # trips_filtered_by_stops_and_times to trip_ids
    #trips_filtered_by_stops_and_times = [x.trip_id for x in trips_filtered_by_stops_and_times]
    arrival_delta_abs_sums_seconds = [y for (y,x) in sorted_trips]
    return trips_filtered_by_stops_and_times, arrival_delta_abs_sums_seconds

cl = get_redis_client()
p = get_redis_pipeline()