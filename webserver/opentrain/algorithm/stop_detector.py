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

HISTORY_LENGTH = 100000

def get_train_tracker_current_stop_id_key(tracker_id):
    return "train_tracker:%s:current_stop_id" % (tracker_id)

def get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id):
    return "train_tracker:%s:timestamp_sorted_stop_ids" % (tracker_id)

def get_train_tracker_tracked_stops_key(tracker_id):
    return "train_tracker:%s:tracked_stops" % (tracker_id)

def get_train_tracker_tracked_stops_prev_stops_counter_key(tracker_id):
    return "train_tracker:%s:tracked_stops:prev_stops_counter" % \
           (tracker_id)

def get_train_tracker_prev_stops_counter_key(tracker_id):
    return "train_tracker:%s:prev_stops_counter" % (tracker_id)


class DetectedStopTime(object):
    def __init__(self, stop_id, arrival=None, departure=None):
        self.stop_id = stop_id
        self.stop_id = stops.all_stops[stop_id].id
        self.name = stops.all_stops[stop_id].name
        self.arrival = arrival
        self.departure = departure
    
    def __str__(self):
        return DetectedStopTime.get_str(self.arrival, self.departure, self.name)
    
    @staticmethod
    def load_from_redis(redis_data):
        arrival = ot_utils.unix_time_to_localtime(int(redis_data[1]))
        redis_data_0_split = redis_data[0].split('_')
        stop_id = redis_data_0_split[0]
        name = stops.all_stops[stop_id].name
        departure = ot_utils.unix_time_to_localtime(int(redis_data_0_split[1])) if redis_data_0_split[1] != '' else None    
        return DetectedStopTime(stop_id, arrival, departure)

    def save_to_redis():
        # TODO - implement
        pass

    @staticmethod
    def get_str(arrival, departure, name):
        arrival_str = arrival.strftime('%H:%M:%S') if arrival is not None else '--:--:--'
        departure_str = departure.strftime('%H:%M:%S') if departure is not None else '--:--:--'
        delta_str = str(departure - arrival).split('.')[0] if departure is not None else '-:--:--'
        return '%s %s %s %s' % (arrival_str, departure_str, delta_str, name)

def setup_hmm():
    stop_count = len(stops.all_stops)

    n_components = stop_count+1 # +1 for non-stop
    n_symbols = n_components
    hmm_non_stop_component_num = n_components-1
    # should probably get these numbers from the data and not guess them :)
    stay_prob = 0.99
    a = np.diag(np.ones(n_components) * stay_prob)
    a[-1,:-1] = (1-stay_prob)/len(a[-1,:-1])
    a[:-1,-1] = (1-stay_prob)
    emissionprob = a
    transmat = a
    startprob = np.ones(n_components)/(n_components) # uniform probability
    hmm = MultinomialHMM(n_components,
                                startprob=startprob,
                                transmat=transmat)        
    hmm._set_emissionprob(emissionprob)
    
    return hmm, hmm_non_stop_component_num        

def update_stop_time(tracker_id, prev_stop_id, arrival_unix_timestamp, stop_id_and_departure_time):
    prev_stops_counter_key = get_train_tracker_tracked_stops_prev_stops_counter_key(tracker_id)
    done = False
    while not done:
        p.watch(prev_stops_counter_key)
        prev_stops_counter_value = cl.get(prev_stops_counter_key)
        if prev_stops_counter_value is None or int(prev_stops_counter_value) < prev_stop_id:
            try:
                p.multi()
                p.zremrangebyscore(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
                p.zadd(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, stop_id_and_departure_time)
                p.set(prev_stops_counter_key, prev_stop_id)
                res = p.execute()
                done = True
            except WatchError:
                done = False
                p.unwatch()
        else:
            done = True
            p.unwatch()


        
 
def add_prev_stop(tracker_id, stop_id, timestamp):
    next_id = cl.incr(get_train_tracker_prev_stops_counter_key(tracker_id))
    #p = get_redis_pipeline()
    #p.set("train_tracker:%s:%d:stop_id:" % (tracker_id, next_id), stop_id)
    unix_timestamp = ot_utils.dt_time_to_unix_time(timestamp)
    p.zadd(get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id), unix_timestamp, "%d_%s" % (next_id, stop_id))
    p.zremrangebyrank(get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id), 0, -HISTORY_LENGTH-1)
    p.execute()
    #p.set("train_tracker:%s:%d:timestamp:" % (tracker_id, next_id), timestamp)
    #p.execute()
    return next_id

def print_tracked_stop_times(tracker_id):
    #for tracked_stop_time in self.stop_times:
    #    print tracked_stop_time
    res = cl.zrange(get_train_tracker_tracked_stops_key(tracker_id), 0, -1, withscores=True)
    for cur in res:
        arrival = ot_utils.unix_time_to_localtime(int(cur[1]))
        cur_0_split = cur[0].split('_')
        name = stops.all_stops[cur_0_split[0]].name
        departure = ot_utils.unix_time_to_localtime(int(cur_0_split[1])) if cur_0_split[1] != '' else None
        print DetectedStopTime.get_str(arrival, departure, name)

def try_get_stop_id(report):
    if report.is_station():
        wifis = [x for x in report.get_wifi_set_all() if x.SSID == 'S-ISRAEL-RAILWAYS']
        wifi_stops_ids = set()
        for wifi in wifis:
            if bssid_tracker.tracker.has_bssid_high_confidence(wifi.key):
                stop_id ,_ ,_ = bssid_tracker.tracker.get_stop_id(wifi.key)
                wifi_stops_ids.add(stop_id)
        
        wifi_stops_ids = np.array(list(wifi_stops_ids))
        
        # check all wifis show same station:
        if len(wifi_stops_ids) > 0 and np.all(wifi_stops_ids == wifi_stops_ids[0]):
            stop_id = wifi_stops_ids[0]
        else:
            stop_id = None          
    else:
        stop_id = nostop_id
           
    return stop_id

def get_detected_stop_times(tracker_id):
    stop_times_redis = cl.zrange(get_train_tracker_tracked_stops_key(\
                                     tracker_id), 0, -1, withscores=True)
    stop_times = []
    for cur in stop_times_redis:
        stop_times.append(DetectedStopTime.load_from_redis(cur))
    return stop_times

def add_report(tracker_id, report):
    # 1) add stop or non-stop to prev_stops and prev_stops_timestamps     
    # 2) set calc_hmm to true if according to wifis and/or location, our
    #    state changed from stop to non-stop or vice versa
    prev_current_stop_id_by_hmm = cl.get(\
        get_train_tracker_current_stop_id_key(tracker_id))
      
    if not prev_current_stop_id_by_hmm:
        prev_state = tracker_states.INITIAL
    elif prev_current_stop_id_by_hmm == stops.NOSTOP:
        prev_state = tracker_states.NOSTOP
    else:
        prev_state = tracker_states.STOP

    stop_id = try_get_stop_id(report)
    if not stop_id:
        current_state = tracker_states.UNKNOWN
    elif stop_id == nostop_id:
        current_state = tracker_states.NOSTOP
    else:
        current_state = tracker_states.STOP

    if current_state != tracker_states.UNKNOWN:
        timestamp = report.get_timestamp_israel_time()
        prev_stop_id = add_prev_stop(tracker_id, stop_id, timestamp)
        
    # calculate hmm to get state_sequence, update stop_times and current_stop if needed
    if  current_state != tracker_states.UNKNOWN and prev_state != current_state:

        prev_stops_and_timestamps = cl.zrange(get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id), 0, -1, withscores=True)
        prev_stop_ids_order = [int(x[0].split("_")[0]) for x in prev_stops_and_timestamps]
        prev_stops_and_timestamps = [x for (y,x) in sorted(zip(prev_stop_ids_order,prev_stops_and_timestamps))]
        
        prev_stop_ids = [x[0].split("_")[1] for x in prev_stops_and_timestamps]
        
        prev_stop_int_ids = np.array([stops.all_stops.id_list.index(x) for x in prev_stop_ids])
        #assert np.array_equal(prev_stop_int_ids, np.array(self.prev_stops))
        prev_stop_hmm_logprob, prev_stop_int_ids_by_hmm = hmm.decode(prev_stop_int_ids)
        prev_stop_int_ids_by_hmm_for_debug = prev_stop_int_ids_by_hmm
        
        # update current_stop_id_by_hmm and current_state by hmm:        
        current_stop_id_by_hmm = stops.all_stops.id_list[prev_stop_int_ids_by_hmm[-1]]
        cl.set(get_train_tracker_current_stop_id_key(tracker_id), current_stop_id_by_hmm)
        if current_stop_id_by_hmm == stops.NOSTOP:
            current_state = tracker_states.NOSTOP
        else:
            current_state = tracker_states.STOP

        if prev_state != current_state: # change in state
            prev_stops_by_hmm = [stops.all_stops.id_list[x] for x in prev_stop_int_ids_by_hmm]
            prev_stops_timestamps = [ot_utils.unix_time_to_localtime((x[1])) for x in prev_stops_and_timestamps]
            index_of_oldest_current_state = max(0, find_index_of_first_consecutive_value(prev_stops_by_hmm, len(prev_stops_by_hmm)-1))
            index_of_most_recent_previous_state = index_of_oldest_current_state-1
              
            if current_state == tracker_states.NOSTOP:
                stop_id = prev_stops_by_hmm[index_of_most_recent_previous_state]
                unix_timestamp = ot_utils.dt_time_to_unix_time(prev_stops_timestamps[index_of_most_recent_previous_state])

                if prev_state == tracker_states.INITIAL:
                    pass #do nothing
                else: # previous_state == tracker_states.STOP - need to set stop_time departure
                    stop_time = cl.zrange(get_train_tracker_tracked_stops_key(tracker_id), -1, -1, withscores=True)
                    departure_unix_timestamp = unix_timestamp
                    stop_id_and_departure_time = "%s_%d" % (prev_current_stop_id_by_hmm, departure_unix_timestamp)
                    update_stop_time(tracker_id, prev_stop_id, stop_time[0][1], stop_id_and_departure_time)
            else: # current_state == tracker_states.STOP
                stop_id = prev_stops_by_hmm[index_of_oldest_current_state]
                unix_timestamp = ot_utils.dt_time_to_unix_time(prev_stops_timestamps[index_of_oldest_current_state])
                
                arrival_unix_timestamp = unix_timestamp
                stop_id_and_departure_time = "%s_" % (current_stop_id_by_hmm)
                update_stop_time(tracker_id, prev_stop_id, arrival_unix_timestamp, stop_id_and_departure_time)
                    
            prev_timestamp = unix_timestamp

    stop_times = get_detected_stop_times(tracker_id)
    return stop_times, prev_state != current_state    
            
hmm, hmm_non_stop_component_num = setup_hmm()
nostop_id = stops.all_stops.id_list[hmm_non_stop_component_num]
tracker_states = enum(INITIAL='initial', NOSTOP='nostop', STOP='stop', UNKNOWN='unknown')

cl = get_redis_client()
p = get_redis_pipeline()