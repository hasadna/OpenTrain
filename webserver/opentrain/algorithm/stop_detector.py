import config
import numpy as np
import stops
from common import ot_utils
import bssid_tracker
from redis_intf.client import (get_redis_pipeline,
                               get_redis_client,
                               load_by_key,
                               save_by_key)
from utils import enum
from redis import WatchError
from alg_logger import logger
import json

HISTORY_LENGTH = 100000
ISRAEL_RAILWAYS_SSID = 'S-ISRAEL-RAILWAYS'


def get_train_tracker_data_key(tracker_id):
    return 'train_tracker:%s:data' % (tracker_id)

def get_train_tracker_tracked_stop_times_key(tracker_id):
    return 'train_tracker:%s:tracked_stop_times' % (tracker_id)

# This key is used for the check-and-set transaction:
def get_train_tracker_report_id_key(tracker_id):
    return 'train_tracker:%s:report_id' % (tracker_id)

# This key is used for the check-and-set transaction:
def get_train_tracker_updated_report_id_key(tracker_id):
    return 'train_tracker:%s:updated_report_id' % (tracker_id)


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
        data = json.loads(redis_data[0])
        stop_id = data[0]
        departure = ot_utils.isoformat_to_localtime(data[1]) if data[1] else None
        return DetectedStopTime(stop_id, arrival, departure)

    @staticmethod
    def load_from_gtfs(gtfs_stop_time, date):
        # TODO: Update this with timetable db changes
        arrival = ot_utils.db_time_to_datetime(
            gtfs_stop_time.exp_arrival, date)
        arrival = ot_utils.get_localtime(arrival)
        departure = ot_utils.db_time_to_datetime(
            gtfs_stop_time.exp_departure, date)
        departure = ot_utils.get_localtime(departure)
        return DetectedStopTime(gtfs_stop_time.stop.stop_id, arrival, departure)

    @staticmethod
    def get_str(arrival, departure, name):
        arrival_str = arrival.strftime(
            '%H:%M:%S') if arrival is not None else '--:--:--'
        departure_str = departure.strftime(
            '%H:%M:%S') if departure is not None else '--:--:--'
        delta_str = str(
            departure - arrival).split('.')[0] if departure is not None else '-:--:--'
        return '%s %s %s %s' % (arrival_str, departure_str, delta_str, name)


class DetectorState(object):

    def __init__(self, tracker_id):
        self.tracker_id = tracker_id

    def get_current(self):
        data = load_by_key(get_train_tracker_data_key(self.tracker_id))
        if data:
            (state, stop_id, timestamp) = data
            timestamp = ot_utils.isoformat_to_localtime(timestamp)
            return state, stop_id, timestamp
        else:
            return DetectorState.states.INITIAL, None, None

    def set_current(self, state, stop_id, timestamp):
        key = get_train_tracker_data_key(
            self.tracker_id)
        value = (state, stop_id, timestamp.isoformat())
        save_by_key(key, value, cl=p)

    states = enum(INITIAL='initial', NOSTOP='nostop',
                  STOP='stop', UNKNOWN_STOP='unknown_stop')
    transitions = enum(NORMAL='normal', NOREPORT_TIMEGAP='noreport_timegap')


def end_stop_time(tracker_id, stop_id, arrival_time, departure_time):
    update_stop_time(tracker_id, arrival_time, stop_id, departure_time)


def end_stop_time_then_start_stop_time(tracker_id, stop_id, arrival_time, departure_time, stop_id2, arrival_time2, is_report_timegap=False):
    end_stop_time(tracker_id, stop_id, arrival_time, departure_time)
    start_stop_time(tracker_id, stop_id2, arrival_time2, is_report_timegap)


def start_stop_time(tracker_id, stop_id, arrival_time, is_report_timegap=False):
    #stop_time = get_last_detected_stop_time(tracker_id)
    # if last station is same station
    #if stop_time and stop_time.stop_id == stop_id and not is_report_timegap:
        ## no timegap
        #if not stop_time or arrival_time - stop_time.arrival < config.no_stop_timegap:
            #arrival_time = stop_time.arrival
    update_stop_time(tracker_id, arrival_time, stop_id, None)


def update_stop_time(tracker_id, arrival_timestamp, stop_id, departure_time, is_report_timegap=False):
    arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(arrival_timestamp)
    departure_time = departure_time.isoformat() if departure_time else None
    stop_id_and_departure_time = json.dumps((stop_id, departure_time))

    stop_time = get_last_detected_stop_time(tracker_id)
    # if last station is same station
    if stop_time and stop_time.stop_id == stop_id and not is_report_timegap:
        # no timegap
        if not stop_time or arrival_timestamp - stop_time.arrival < config.no_stop_timegap:
            arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(
                stop_time.arrival)
    arrival_unix_timestamp = int(arrival_unix_timestamp)

    p.zremrangebyscore(get_train_tracker_tracked_stop_times_key(
        tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
    p.zadd(get_train_tracker_tracked_stop_times_key(tracker_id),
           arrival_unix_timestamp, stop_id_and_departure_time)


def print_tracked_stop_times(tracker_id):
    stop_times = get_detected_stop_times(tracker_id)
    for stop_time in stop_times:
        print stop_time


def get_report_data(report):
    if report.is_station():
        wifis = [
            x for x in report.get_wifi_set_all() if x.SSID == ISRAEL_RAILWAYS_SSID]
        wifi_stops_ids = set()
        for wifi in wifis:
            if bssid_tracker.tracker.has_bssid_high_confidence(wifi.key):
                stop_id, _, _ = bssid_tracker.tracker.get_stop_id(wifi.key)
                wifi_stops_ids.add(stop_id)

        wifi_stops_ids = np.array(list(wifi_stops_ids))

        # check all wifis show same station:
        if len(wifi_stops_ids) > 0 and np.all(wifi_stops_ids == wifi_stops_ids[0]):
            stop_id = wifi_stops_ids[0]
            state = DetectorState.states.STOP
        else:
            logger.debug('No stop for bssids: %s' %
                         ','.join([x.key for x in wifis]))
            stop_id = None
            state = DetectorState.states.UNKNOWN_STOP
    else:
        stop_id = stops.NOSTOP_ID
        state = DetectorState.states.NOSTOP

    timestamp = report.get_timestamp_israel_time()
    return state, stop_id, timestamp


def get_detected_stop_times(tracker_id, last_n=0):
    stop_times_redis = cl.zrange(get_train_tracker_tracked_stop_times_key(
        tracker_id), last_n*-1, -1, withscores=True)
    stop_times = []
    for cur in stop_times_redis:
        stop_times.append(DetectedStopTime.load_from_redis(cur))
    return stop_times


def get_last_detected_stop_time(tracker_id):
    stop_times = get_detected_stop_times(tracker_id, last_n=1)
    if len(stop_times) > 0:
        return stop_times[0]
    else:
        return None


def add_report(tracker_id, report):
    is_updated_stop_time = False
    report_id = cl.incr(get_train_tracker_report_id_key(tracker_id))
    updated_report_id_key = get_train_tracker_updated_report_id_key(
        tracker_id)
    # We try to update a report only if no report was updated with a more recent 
    # report_id than us. If one was updated, we don't update at all. 
    # This is done using check-and-set (see http://redis.io/topics/transactions)
    done = False
    while not done:
        p.watch(updated_report_id_key)
        updated_report_id = load_by_key(updated_report_id_key)
        if not updated_report_id or updated_report_id < report_id:
            try:
                p.multi()
                is_updated_stop_time = try_add_report(tracker_id, report)
                p.set(updated_report_id_key, report_id)
                p.execute()
                done = True
            except WatchError:
                done = False
                p.unwatch()
        else:
            done = True
            p.unwatch()
    return is_updated_stop_time and done


def try_add_report(tracker_id, report):
    is_updated_stop_time = False
    
    detector_state = DetectorState(tracker_id)
    prev_state, prev_stop_id, prev_timestamp = detector_state.get_current()
    # new report is older than last report:
    if prev_timestamp and report.timestamp < prev_timestamp:
        return None

    state, stop_id, timestamp = get_report_data(report)
    if prev_timestamp and timestamp - prev_timestamp > config.no_report_timegap:
        detector_state_transition = DetectorState.transitions.NOREPORT_TIMEGAP
    else:
        detector_state_transition = DetectorState.transitions.NORMAL

    detector_state.set_current(state, stop_id, timestamp)

    if prev_state in [DetectorState.states.INITIAL, DetectorState.states.NOSTOP]:
        if state == DetectorState.states.NOSTOP:
            pass
        elif state == DetectorState.states.STOP:
            start_stop_time(tracker_id, stop_id,
                            timestamp)
            is_updated_stop_time = True
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            pass
    elif prev_state == DetectorState.states.STOP:
        if state == DetectorState.states.NOSTOP:
            # previous_state == tracker_states.STOP - need to set stop_time
            # departure
            stop_time = get_last_detected_stop_time(tracker_id)
            end_stop_time(
                tracker_id, prev_stop_id, stop_time.arrival, prev_timestamp)
            is_updated_stop_time = True
        elif state == DetectorState.states.STOP:
            if detector_state_transition == DetectorState.transitions.NOREPORT_TIMEGAP:
                stop_time = get_last_detected_stop_time(tracker_id)
                print 'NOREPORT_TIMEGAP'
                end_stop_time_then_start_stop_time(tracker_id, prev_stop_id, 
                                                   stop_time.arrival,
                                                   prev_timestamp,
                                                   prev_stop_id, 
                                                   timestamp, 
                                                   True)
                is_updated_stop_time = True
            elif prev_stop_id != stop_id:
                assert False, 'check this code works'
                stop_time = get_last_detected_stop_time(tracker_id)
                end_stop_time_then_start_stop_time(tracker_id,
                                                   prev_stop_id,
                                                   stop_time.arrival,
                                                   prev_timestamp,
                                                   prev_stop_id,
                                                   prev_timestamp)
                is_updated_stop_time = True
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            pass
    elif prev_state == DetectorState.states.UNKNOWN_STOP:
        if state == DetectorState.states.NOSTOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            pass
        elif state == DetectorState.states.STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            pass
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            pass

    return is_updated_stop_time


cl = get_redis_client()
p = get_redis_pipeline()
