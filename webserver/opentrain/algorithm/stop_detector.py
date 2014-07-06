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
        arrival = ot_utils.db_time_to_datetime(gtfs_stop_time.arrival_time, date)
        arrival = ot_utils.get_localtime(arrival)
        departure = ot_utils.db_time_to_datetime(gtfs_stop_time.departure_time, date)
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
        if detector_state_transition == detector_state_transitions.NOREPORT_TIMEGAP:
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
        return stop_id, unix_timestamp

    def get_most_recent_previous_state_data(self, detector_state_transition):
        _, index_of_most_recent_previous_state = self._get_previous_state_inds(detector_state_transition, self.prev_stop_int_ids)
        stop_id = stops.all_stops.id_list[self.prev_stop_int_ids[index_of_most_recent_previous_state]]
        unix_timestamp = self.prev_stops_and_timestamps[index_of_most_recent_previous_state][1]        
        return stop_id, unix_timestamp

def update_stop_time(tracker_id, prev_stop_id, arrival_unix_timestamp, stop_id, departure_time, arrival_unix_timestamp2=None, stop_id_and_departure_time2=None, is_report_timegap=False):
    if departure_time:
        stop_id_and_departure_time = "%s_%d" % (stop_id, departure_time)
    else:
        stop_id_and_departure_time = "%s_" % stop_id
    arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(arrival_unix_timestamp)
    print_tracked_stop_times(tracker_id)
    print 'stop', stop_id_and_departure_time.split('_')[0]
    print 'arrival', ot_utils.unix_time_to_localtime(arrival_unix_timestamp)
    if stop_id_and_departure_time.split('_')[1]:
        print 'departure', ot_utils.unix_time_to_localtime(int(stop_id_and_departure_time.split('_')[1]))
    else:
        print 'no departure'
    if arrival_unix_timestamp2:    
        print 'arrival2', ot_utils.unix_time_to_localtime(arrival_unix_timestamp2)
        print 'departure2', ot_utils.unix_time_to_localtime(int(stop_id_and_departure_time2.split('_')[1]))
    
    stop_times = get_detected_stop_times(tracker_id)
    if len(stop_times) > 0 and stop_times[-1].stop_id == int(stop_id_and_departure_time.split('_')[0]) and not is_report_timegap: # if last station is same station
        arrival_timestamp = ot_utils.unix_time_to_localtime(arrival_unix_timestamp)
        if not stop_times or arrival_timestamp - stop_times[-1].arrival < config.no_stop_timegap:  # no timegap
            arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(stop_times[-1].arrival)
    prev_stops_counter_key = get_train_tracker_tracked_stops_prev_stops_counter_key(tracker_id)
    done = False
    # we try to update a stop_time only if no stop_time was updated since we started the report processing. If one was updated, we don't update at all:
    arrival_unix_timestamp = int(arrival_unix_timestamp)
    
    while not done:
        p.watch(prev_stops_counter_key)
        prev_stops_counter_value = cl.get(prev_stops_counter_key)
        if prev_stops_counter_value is None or int(prev_stops_counter_value) < prev_stop_id:
            try:
                p.multi()
                p.zremrangebyscore(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
                p.zadd(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp, stop_id_and_departure_time)
                if arrival_unix_timestamp2:
                    p.zremrangebyscore(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp2, arrival_unix_timestamp2)
                    p.zadd(get_train_tracker_tracked_stops_key(tracker_id), arrival_unix_timestamp2, stop_id_and_departure_time2)
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

    detector_state_transition = detector_state_transitions.NORMAL
    if not prev_stop_id:
        prev_state = detector_states.INITIAL
    else:
        data = detector_state.get_prev_stop_data()
        if report.timestamp - ot_utils.unix_time_to_localtime(data[0][-1][1]) > config.no_report_timegap:
            detector_state_transition = detector_state_transitions.NOREPORT_TIMEGAP
        prev_state = prev_stop_id

    stop_id = try_get_stop_id(report)
    current_state = stop_id if stop_id else detector_states.UNKNOWN

    if current_state != detector_states.UNKNOWN:
        timestamp = report.get_timestamp_israel_time()
        prev_report_id = add_prev_stop(tracker_id, stop_id, timestamp)

    # calculate hmm to get state_sequence, update stop_times and current_stop if needed
    if  current_state != detector_states.UNKNOWN and prev_state != current_state:

        prev_stops_and_timestamps, prev_stop_int_ids = detector_state.get_prev_stop_data()

        current_state = stops.all_stops.id_list[prev_stop_int_ids[-1]]
        detector_state.set_current(current_state, str(prev_stops_and_timestamps[-1][1]))

        if prev_state != current_state: # change in state
            if current_state == stops.NOSTOP_ID:
                stop_id, unix_timestamp = detector_state.get_most_recent_previous_state_data(detector_state_transition)

                if prev_state == detector_states.INITIAL:
                    pass #do nothing
                else: # previous_state == tracker_states.STOP - need to set stop_time departure
                    stop_time = get_last_detected_stop_time(tracker_id)
                    departure_unix_timestamp = unix_timestamp
                    stop_id_and_departure_time = "%s_%d" % (prev_stop_id, departure_unix_timestamp)
                    update_stop_time(tracker_id, prev_report_id, stop_time.arrival, prev_stop_id, departure_unix_timestamp)
            else: # current_state == tracker_states.STOP
                arrival_unix_timestamp_prev_stop = None
                stop_id_and_departure_time_prev_stop = None
                if (prev_state != detector_states.INITIAL and prev_state != stops.NOSTOP_ID):
                    stop_time = get_last_detected_stop_time(tracker_id)
                    departure_unix_timestamp = ot_utils.dt_time_to_unix_time(prev_timestamp) 
                    stop_id_and_departure_time = "%s_%d" % (prev_stop_id, departure_unix_timestamp)
                    arrival_unix_timestamp_prev_stop = stop_time.arrival
                    stop_id_and_departure_time_prev_stop = stop_id_and_departure_time
                    
                stop_id, unix_timestamp = detector_state.get_oldest_current_state_data(detector_state_transition)
  
                arrival_unix_timestamp = ot_utils.unix_time_to_localtime(unix_timestamp)
                update_stop_time(tracker_id, prev_report_id, arrival_unix_timestamp, current_state, None, arrival_unix_timestamp_prev_stop, stop_id_and_departure_time_prev_stop)
            print unix_timestamp
            prev_timestamp = ot_utils.unix_time_to_localtime(unix_timestamp)
    elif detector_state_transition == detector_state_transitions.NOREPORT_TIMEGAP:
        stop_time = cl.zrange(get_train_tracker_tracked_stops_key(tracker_id), -1, -1, withscores=True)
        prev_stops_and_timestamps, prev_stop_int_ids = detector_state.get_prev_stop_data()
        stop_id, unix_timestamp = detector_state.get_most_recent_previous_state_data(detector_state_transition)
        arrival_unix_timestamp_prev_stop = stop_time[0][1]
        stop_id_and_departure_time_prev_stop = "%s_%d" % (stop_id, unix_timestamp)
        # XXX todo - take care of the case when current_state == detector_states.UNKNOWN
        arrival_unix_timestamp = report.timestamp
        departure_unix_timestamp = unix_timestamp
        print 'NOREPORT_TIMEGAP'
        update_stop_time(tracker_id, prev_report_id, arrival_unix_timestamp, current_state, None, arrival_unix_timestamp_prev_stop, stop_id_and_departure_time_prev_stop, True)        
        

    stop_times = get_detected_stop_times(tracker_id)
    is_stops_updated = (prev_state != current_state) and current_state != detector_states.UNKNOWN and len(stop_times) > 0
    return stop_times, is_stops_updated


detector_states = enum(INITIAL='initial', NOSTOP='nostop', STOP='stop', UNKNOWN='unknown')
detector_state_transitions = enum(NORMAL='normal', NOREPORT_TIMEGAP='noreport_timegap', NOSTOP_TIMEGAP='nostop_timegap')

cl = get_redis_client()
p = get_redis_pipeline()