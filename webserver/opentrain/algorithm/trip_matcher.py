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
def get_matched_trips(tracker_id, detected_stop_times, relevant_service_ids, day):
    if len(detected_stop_times) == 0:
        return None, None
    trip_datastore = TripDatastore(day)
    costops = trip_datastore.costop_matrix
    
    stop_ids = [x.stop_id for x in detected_stop_times]
    stop_ids_inds = [all_stops.id_list.index(x) for x in stop_ids]

    impossible_stops_inds = trip_datastore.GetImpossibleCostops(stop_ids_inds)
    trips_with_visited_stops = trip_datastore.GetTripsByStops(stop_ids_inds)
    trips_with_impossible_stops = trip_datastore.GetTripsByStops(impossible_stops_inds)
    trips_filtered_by_stops = list(set(trips_with_visited_stops) - set(trips_with_impossible_stops))

    # filter by stop order and at least two detected stops:
    trip_in_right_direction = []
    for i, t in enumerate(trips_filtered_by_stops):
        detected_stop_ids = [x.stop_id for x in detected_stop_times]   
        stops = trip_datastore.trip_datastore[t]['stops']
        trip_stop_times = [stops[x] for x in detected_stop_ids if x in stops]
        if len(trip_stop_times) >= 2:
            gtfs_arrival_of_detected_stops = [x[0] for x in trip_stop_times]
            if is_increasing(gtfs_arrival_of_detected_stops):
                trip_in_right_direction.append(i)
    trips_filtered_by_stop_order = [trips_filtered_by_stops[i] for i in trip_in_right_direction]
    
    # order by deviation from gtfs arrival time:
    arrival_delta_abs_sums_seconds = []
    for t in trips_filtered_by_stop_order:
        stop_times_gtfs = trip_datastore.trip_datastore[t]['stops']
        arrival_delta_abs_sum = 0
        for detected_stop_time in detected_stop_times:
            stop_and_arrival_gtfs = stop_times_gtfs.get(detected_stop_time.stop_id)
            if stop_and_arrival_gtfs:
                arrival_delta_seconds = stop_and_arrival_gtfs[1] - datetime_to_db_time(detected_stop_time.arrival)
                arrival_delta_abs_sum += abs(arrival_delta_seconds)
        arrival_delta_abs_sums_seconds.append(arrival_delta_abs_sum)
    
    sorted_trips = sorted(zip(arrival_delta_abs_sums_seconds,trips_filtered_by_stop_order))
    trips_filtered_by_stop_order = [x for (y,x) in sorted_trips]
    arrival_delta_abs_sums_seconds = [y for (y,x) in sorted_trips]
    
    return trips_filtered_by_stop_order, arrival_delta_abs_sums_seconds

cl = get_redis_client()
p = get_redis_pipeline()