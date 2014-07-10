from scipy import spatial
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
import bssid_tracker 
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
from utils import enum
from redis import WatchError
from alg_logger import logger

HISTORY_LENGTH = 100000

def get_train_tracker_current_stop_id_and_timestamp_key(tracker_id):
    return "train_tracker:%s:current_stop_id_and_timestamp" % (tracker_id)

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
    
    def __repr__(self):
        return self.__str__()
    
    @staticmethod
    def load_from_redis(redis_data):
        arrival = ot_utils.unix_time_to_localtime(int(redis_data[1]))
        redis_data_0_split = redis_data[0].split('_')
        stop_id = int(redis_data_0_split[0])
        name = stops.all_stops[stop_id].name
        departure = ot_utils.unix_time_to_localtime(int(redis_data_0_split[1])) if redis_data_0_split[1] != '' else None    
        return DetectedStopTime(stop_id, arrival, departure)

    @staticmethod
    def load_from_gtfs(gtfs_stop_time, date):
        arrival = ot_utils.db_time_to_datetime(gtfs_stop_time.exp_arrival, date)
        arrival = ot_utils.get_localtime(arrival)
        departure = ot_utils.db_time_to_datetime(gtfs_stop_time.exp_departure, date)
        departure = ot_utils.get_localtime(departure)        
        return DetectedStopTime(gtfs_stop_time.stop.stop_id, arrival, departure)        

    def save_to_redis():
        # TODO - implement
        pass

    @staticmethod
    def get_str(arrival, departure, name):
        arrival_str = arrival.strftime('%H:%M:%S') if arrival is not None else '--:--:--'
        departure_str = departure.strftime('%H:%M:%S') if departure is not None else '--:--:--'
        delta_str = str(departure - arrival).split('.')[0] if departure is not None else '-:--:--'
        return '%s %s %s %s' % (arrival_str, departure_str, delta_str, name)

class DetectorState(object):
    def __init__(self, tracker_id):
        self.tracker_id = tracker_id
    
    def get_current(self):
        current_stop_id_and_timestamp = cl.get(\
            get_train_tracker_current_stop_id_and_timestamp_key(self.tracker_id))
        if current_stop_id_and_timestamp:
            current_stop_id = current_stop_id_and_timestamp.split("_")[0]
            current_timestamp = current_stop_id_and_timestamp.split("_")[1]
            current_stop_id = int(current_stop_id)
            current_timestamp = float(current_timestamp)
            current_timestamp = ot_utils.unix_time_to_localtime(current_timestamp)
        else:
            current_stop_id = None
            current_timestamp = None
        return current_stop_id, current_timestamp
    
    def set_current(self, stop_id, timestamp):
        cl.set(get_train_tracker_current_stop_id_and_timestamp_key(self.tracker_id), str(stop_id) + "_" + str(timestamp))
    
    def get_prev_stop_data(self):
        tracker_id = self.tracker_id
        prev_stops_and_timestamps = cl.zrange(get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id), 0, -1, withscores=True)
        prev_stop_ids_order = [int(x[0].split("_")[0]) for x in prev_stops_and_timestamps]
        prev_stops_and_timestamps = [x for (y,x) in sorted(zip(prev_stop_ids_order,prev_stops_and_timestamps))]
        
        prev_stop_ids = [int(x[0].split("_")[1]) for x in prev_stops_and_timestamps]
    
        prev_stop_int_ids = np.array([stops.all_stops.id_list.index(x) for x in prev_stop_ids])
        self.prev_stop_int_ids = prev_stop_int_ids
        self.prev_stops_and_timestamps = prev_stops_and_timestamps
        return prev_stops_and_timestamps, prev_stop_int_ids    
    
    def _get_previous_state_inds(self, detector_state_transition, prev_stop_int_ids):
        if detector_state_transition == DetectorState.transitions.NOREPORT_TIMEGAP:
            # after a time gap, we're essentially in a new state:
            index_of_oldest_current_state = len(prev_stop_int_ids) - 1
        else:
            index_of_oldest_current_state = max(0, find_index_of_first_consecutive_value(prev_stop_int_ids, len(prev_stop_int_ids)-1))
        index_of_most_recent_previous_state = index_of_oldest_current_state-1
        return index_of_oldest_current_state, index_of_most_recent_previous_state    

    def get_oldest_current_state_data(self, detector_state_transition):
        index_of_oldest_current_state, _ = self._get_previous_state_inds(detector_state_transition, self.prev_stop_int_ids)
        stop_id = stops.all_stops.id_list[self.prev_stop_int_ids[index_of_oldest_current_state]]
        unix_timestamp = self.prev_stops_and_timestamps[index_of_oldest_current_state][1]        
        timestamp = ot_utils.unix_time_to_localtime(unix_timestamp)
        return stop_id, timestamp

    def get_most_recent_previous_state_data(self, detector_state_transition):
        _, index_of_most_recent_previous_state = self._get_previous_state_inds(detector_state_transition, self.prev_stop_int_ids)
        stop_id = stops.all_stops.id_list[self.prev_stop_int_ids[index_of_most_recent_previous_state]]
        unix_timestamp = self.prev_stops_and_timestamps[index_of_most_recent_previous_state][1]        
        return stop_id, ot_utils.unix_time_to_localtime(unix_timestamp)
    
    states = enum(INITIAL='initial', NOSTOP='nostop', STOP='stop', UNKNOWN_STOP='unknown_stop')
    transitions = enum(NORMAL='normal', NOREPORT_TIMEGAP='noreport_timegap')
    

def end_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_timestamp):
    update_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_timestamp)
    
def end_stop_time_then_start_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_timestamp, stop_id2, arrival_timestamp2, is_report_timegap = False):
    update_stop_time(tracker_id, prev_stop_id, stop_id2, arrival_timestamp2, None, stop_id, arrival_timestamp, departure_timestamp, is_report_timegap)    

def start_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp):
    update_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, 
                     None)

def update_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_time, stop_id_prev=None, arrival_unix_timestamp_prev=None, departure_time_prev=None, is_report_timegap = False):
    arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(arrival_timestamp)    
    if arrival_unix_timestamp_prev:
        arrival_unix_timestamp_prev = ot_utils.dt_time_to_unix_time(arrival_unix_timestamp_prev)    
    departure_time = ot_utils.dt_time_to_unix_time(departure_time) if departure_time else None
    if departure_time:
        stop_id_and_departure_time = "%s_%d" % (stop_id, departure_time)
    else:
        stop_id_and_departure_time = "%s_" % stop_id
    if stop_id_prev:
        if departure_time_prev:
            stop_id_and_departure_time_prev = "%s_%d" % (stop_id_prev, departure_time_prev)
        else:
            stop_id_and_departure_time_prev = "%s_" % stop_id_prev  
    stop_times = get_detected_stop_times(tracker_id)
    if len(stop_times) > 0 and stop_times[-1].stop_id == int(stop_id_and_departure_time.split('_')[0]) and not is_report_timegap: # if last station is same station
        arrival_timestamp = ot_utils.unix_time_to_localtime(arrival_unix_timestamp)
        if not stop_times or arrival_timestamp - stop_times[-1].arrival < config.no_stop_timegap:  # no timegap
            arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(stop_times[-1].arrival)

    prev_stops_counter_key = get_train_tracker_tracked_stops_prev_stops_counter_key(tracker_id)
    done = False
    # we try to update a stop_time only if no stop_time was updated since we started the report processing. If one was updated, we don't update at all:
    
    while not done:
        p.watch(prev_stops_counter_key)
        prev_stops_counter_value = cl.get(prev_stops_counter_key)
        if prev_stops_counter_value is None or int(prev_stops_counter_value) < prev_stop_id:
            try:
                p.multi()
                p.zremrangebyscore(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
                p.zadd(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, stop_id_and_departure_time)
                if arrival_unix_timestamp_prev:
                    p.zremrangebyscore(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp_prev, arrival_unix_timestamp_prev)
                    p.zadd(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp_prev, stop_id_and_departure_time_prev)
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
        name = stops.all_stops[int(cur_0_split[0])].name
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
            logger.debug('No stop for bssids: %s' % ','.join([x.key for x in wifis]))
            stop_id = None
    else:
        stop_id = stops.NOSTOP_ID
           
    return stop_id

def get_detected_stop_times(tracker_id):
    stop_times_redis = cl.zrange(get_train_tracker_tracked_stops_key(\
                                     tracker_id), 0, -1, withscores=True)
    stop_times = []
    for cur in stop_times_redis:
        stop_times.append(DetectedStopTime.load_from_redis(cur))
    return stop_times

def get_last_detected_stop_time(tracker_id):
    redis_stop_time = cl.zrange(get_train_tracker_tracked_stops_key(tracker_id), -1, -1, withscores=True)
    if len(redis_stop_time) > 0:
        redis_stop_time = redis_stop_time[0]
    else:
        return None
    return DetectedStopTime.load_from_redis(redis_stop_time)

def add_report(tracker_id, report):
    detector_state = DetectorState(tracker_id)
    prev_stop_id, prev_timestamp = detector_state.get_current()

    detector_state_transition = DetectorState.transitions.NORMAL
    if not prev_stop_id:
        prev_state = DetectorState.states.INITIAL
    else:
        data = detector_state.get_prev_stop_data()
        if report.timestamp - ot_utils.unix_time_to_localtime(data[0][-1][1]) > config.no_report_timegap:
            detector_state_transition = DetectorState.transitions.NOREPORT_TIMEGAP
        prev_state = prev_stop_id

    stop_id = try_get_stop_id(report)
    current_state = stop_id if stop_id else DetectorState.states.UNKNOWN_STOP

    if current_state != DetectorState.states.UNKNOWN_STOP:
        timestamp = report.get_timestamp_israel_time()
        prev_report_id = add_prev_stop(tracker_id, stop_id, timestamp)

    # calculate hmm to get state_sequence, update stop_times and current_stop if needed
    if  current_state != DetectorState.states.UNKNOWN_STOP and prev_state != current_state:

        prev_stops_and_timestamps, prev_stop_int_ids = detector_state.get_prev_stop_data()

        current_state = stops.all_stops.id_list[prev_stop_int_ids[-1]]
        detector_state.set_current(current_state, str(prev_stops_and_timestamps[-1][1]))

        if prev_state != current_state: # change in state
            if current_state == stops.NOSTOP_ID:
                stop_id, timestamp = detector_state.get_most_recent_previous_state_data(detector_state_transition)

                if prev_state == DetectorState.states.INITIAL:
                    pass #do nothing
                else: # previous_state == tracker_states.STOP - need to set stop_time departure
                    stop_time = get_last_detected_stop_time(tracker_id)
                    end_stop_time(tracker_id, prev_report_id, prev_stop_id, stop_time.arrival, timestamp)
            else: # current_state == tracker_states.STOP
                arrival_unix_timestamp_prev_stop = None
                stop_id_prev_stop = None
                departure_time_prev_stop = None
                if (prev_state != DetectorState.states.INITIAL and prev_state != stops.NOSTOP_ID):
                    stop_time = get_last_detected_stop_time(tracker_id)
                    departure_time_prev_stop = ot_utils.dt_time_to_unix_time(prev_timestamp) 
                    arrival_unix_timestamp_prev_stop = stop_time.arrival
                stop_id, timestamp = detector_state.get_oldest_current_state_data(detector_state_transition)

                if arrival_unix_timestamp_prev_stop == None:
                    start_stop_time(tracker_id, prev_report_id, current_state, 
                                 timestamp)
                else:
                    end_stop_time_then_start_stop_time(tracker_id, 
                                                      prev_stop_id, 
                                                      current_state, 
                                                      timestamp, 
                                                      arrival_unix_timestamp_prev_stop,
                                                      prev_stop_id, 
                                                      departure_time_prev_stop)
            prev_timestamp = timestamp
    elif detector_state_transition == DetectorState.transitions.NOREPORT_TIMEGAP:
        stop_time = get_last_detected_stop_time(tracker_id)
        prev_stops_and_timestamps, prev_stop_int_ids = detector_state.get_prev_stop_data()
        stop_id, timestamp = detector_state.get_most_recent_previous_state_data(detector_state_transition)
        # XXX todo - take care of the case when current_state == DetectorState.states.UNKNOWN
        print 'NOREPORT_TIMEGAP'
        end_stop_time_then_start_stop_time(tracker_id, prev_report_id, 
                                          stop_id, 
                                          stop_time.arrival, ot_utils.dt_time_to_unix_time(timestamp), current_state, 
                                          report.timestamp, True)

    stop_times = get_detected_stop_times(tracker_id)
    is_stops_updated = (prev_state != current_state) and current_state != DetectorState.states.UNKNOWN_STOP and len(stop_times) > 0
    return stop_times, is_stops_updated


cl = get_redis_client()
p = get_redis_pipeline()

