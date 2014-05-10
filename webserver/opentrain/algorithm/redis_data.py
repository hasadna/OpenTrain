# This file contains functions to load data to redis, usually after a redis reset.
import bssid_tracker
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import gtfs.models
import os
import config
import numpy as np
import stops
import shapes
from utils import *
from common.ot_utils import *
from common import ot_utils
import datetime
import json

GTFS_COSTOP_MATRIX_KEY = 'gtfs:costop_matrix'

def generate_costop_matrix(costop_matrix_date=None):
    if not costop_matrix_date:
        costop_matrix_date = ot_utils.get_localtime_now()
    start_date = costop_matrix_date.strftime("%Y-%m-%d")
    relevant_services = gtfs.models.Service.objects.filter(start_date = start_date)
    relevant_service_ids = [x[0] for x in relevant_services.all().values_list('service_id')]
    trips = gtfs.models.Trip.objects.filter(service__in=relevant_service_ids)
    trips = trips.prefetch_related('stoptime_set', 'stoptime_set__stop')    
    trips = list(trips)
    costops = np.zeros((len(stops.all_stops), len(stops.all_stops)))
    stop_id_to_ind_id = dict(zip(stops.all_stops.id_list, range(len(stops.all_stops.id_list))))
    stops.all_stops.id_list
    for trip in trips:
        trip_stop_times = trip.get_stop_times()
        for stop_time1 in trip_stop_times:
            for stop_time2 in trip_stop_times:
                stop_time1_ind = stop_id_to_ind_id[stop_time1.stop.stop_id];
                stop_time2_ind = stop_id_to_ind_id[stop_time2.stop.stop_id];
                costops[stop_time1_ind, stop_time2_ind] += 1
                costops[stop_time2_ind, stop_time1_ind] += 1
    names = [stops.all_stops[x].name for x in stops.all_stops.id_list[0:-1]]
    if (0):
        import matplotlib.pyplot as plt
        plt.imshow(costops > 0, interpolation="none")
        plt.yticks(range(costops.shape[0]), names, size='small')
        locs, labels = plt.xticks(range(costops.shape[0]), names, size='small')
        plt.setp(labels, rotation=90)

    return (costops > 0).astype(int);

def get_costop_matrix():
    costops_json = load_by_key(GTFS_COSTOP_MATRIX_KEY)
    costops = json.loads(costops_json)
    #plt.imshow(np.array(costops_loaded))
    costops = np.array(costops)    
    return costops

def reload_redis_gtfs_data():
    # bssid_tracker:
    bssid_tracker.calc_tracker()
    # costop matrix:
    costops = generate_costop_matrix() 
    costops_json = json.dumps(costops.tolist())
    save_by_key(GTFS_COSTOP_MATRIX_KEY, costops_json)
    
if __name__ == '__main__':
    reload_redis_gtfs_data()
    
    