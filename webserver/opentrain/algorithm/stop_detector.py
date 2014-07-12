import os
import config
import numpy as np
import stops
from common import ot_utils
from utils import find_index_of_first_consecutive_value
# try:
#import matplotlib.pyplot as plt
# except ImportError:
# pass
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


def get_train_tracker_current_state_stop_id_and_timestamp_key(tracker_id):
    return 'train_tracker:%s:current_state_stop_id_and_timestamp' % (tracker_id)


def get_train_tracker_timestamp_sorted_stop_ids_key(tracker_id):
    return 'train_tracker:%s:timestamp_sorted_stop_ids' % (tracker_id)


def get_train_tracker_tracked_stops_key(tracker_id):
    return 'train_tracker:%s:tracked_stops' % (tracker_id)


def get_train_tracker_tracked_stops_prev_stops_counter_key(tracker_id):
    return 'train_tracker:%s:tracked_stops:prev_stops_counter' % \
           (tracker_id)


def get_train_tracker_prev_stops_counter_key(tracker_id):
    return 'train_tracker:%s:prev_stops_counter' % (tracker_id)


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
        departure = ot_utils.isoformat_to_localtime(
            redis_data_0_split[1]) if redis_data_0_split[1] != '' else None
        return DetectedStopTime(stop_id, arrival, departure)

    @staticmethod
    def load_from_gtfs(gtfs_stop_time, date):
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
        redis_data = cl.get(
            get_train_tracker_current_state_stop_id_and_timestamp_key(self.tracker_id))
        if redis_data:
            (state, stop_id, timestamp) = json.loads(redis_data)
            timestamp = ot_utils.isoformat_to_localtime(timestamp)
        else:
            stop_id = None
            timestamp = None
            state = DetectorState.states.INITIAL

        return state, stop_id, timestamp

    def set_current(self, state, stop_id, timestamp):
        key = get_train_tracker_current_state_stop_id_and_timestamp_key(
            self.tracker_id)
        value = (state, stop_id, timestamp.isoformat())
        save_by_key(key, value)

    states = enum(INITIAL='initial', NOSTOP='nostop',
                  STOP='stop', UNKNOWN_STOP='unknown_stop')
    transitions = enum(NORMAL='normal', NOREPORT_TIMEGAP='noreport_timegap')


def end_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_timestamp):
    update_stop_time(tracker_id, prev_stop_id, arrival_timestamp,
                     stop_id, departure_timestamp)


def end_stop_time_then_start_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp, departure_timestamp, stop_id2, arrival_timestamp2):
    update_stop_time(tracker_id, prev_stop_id, arrival_timestamp,
                     stop_id, departure_timestamp, arrival_timestamp2, stop_id2)


def start_stop_time(tracker_id, prev_stop_id, stop_id, arrival_timestamp):
    update_stop_time(tracker_id, prev_stop_id, arrival_timestamp,
                     stop_id, None)


def update_stop_time(tracker_id, prev_stop_id, arrival_timestamp, stop_id, departure_time, arrival_timestamp2=None, stop_id2=None, departure_time2=None, is_report_timegap=False):
    arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(arrival_timestamp)
    if arrival_timestamp2:
        arrival_unix_timestamp2 = ot_utils.dt_time_to_unix_time(
            arrival_timestamp2)
    departure_time = departure_time.isoformat() if departure_time else None
    departure_time2 = departure_time2.isoformat() if departure_time2 else None
    if departure_time:
        stop_id_and_departure_time = '%s_%s' % (stop_id, departure_time)
    else:
        stop_id_and_departure_time = '%s_' % stop_id
    if stop_id2:
        if departure_time2:
            stop_id_and_departure_time2 = '%s_%s' % (stop_id2, departure_time2)
        else:
            stop_id_and_departure_time2 = '%s_' % stop_id2

    stop_times = get_detected_stop_times(tracker_id)
    # if last station is same station
    if len(stop_times) > 0 and stop_times[-1].stop_id == int(stop_id_and_departure_time.split('_')[0]) and not is_report_timegap:
        # no timegap
        if not stop_times or arrival_timestamp - stop_times[-1].arrival < config.no_stop_timegap:
            arrival_unix_timestamp = ot_utils.dt_time_to_unix_time(
                stop_times[-1].arrival)
    prev_stops_counter_key = get_train_tracker_tracked_stops_prev_stops_counter_key(
        tracker_id)
    done = False
    # we try to update a stop_time only if no stop_time was updated since we
    # started the report processing. If one was updated, we don't update at
    # all:
    arrival_unix_timestamp = int(arrival_unix_timestamp)

    while not done:
        p.watch(prev_stops_counter_key)
        prev_stops_counter_value = cl.get(prev_stops_counter_key)
        if prev_stops_counter_value is None or int(prev_stops_counter_value) < prev_stop_id:
            try:
                p.multi()
                p.zremrangebyscore(get_train_tracker_tracked_stops_key(
                    tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
                p.zadd(get_train_tracker_tracked_stops_key(tracker_id),
                       arrival_unix_timestamp, stop_id_and_departure_time)
                if arrival_timestamp2:
                    p.zremrangebyscore(get_train_tracker_tracked_stops_key(
                        tracker_id), arrival_unix_timestamp2, arrival_unix_timestamp2)
                    p.zadd(get_train_tracker_tracked_stops_key(
                        tracker_id), arrival_unix_timestamp2, stop_id_and_departure_time2)
                p.set(prev_stops_counter_key, prev_stop_id)
                p.execute()
                done = True
            except WatchError:
                done = False
                p.unwatch()
        else:
            done = True
            p.unwatch()


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


def get_detected_stop_times(tracker_id):
    stop_times_redis = cl.zrange(get_train_tracker_tracked_stops_key(
        tracker_id), 0, -1, withscores=True)
    stop_times = []
    for cur in stop_times_redis:
        stop_times.append(DetectedStopTime.load_from_redis(cur))
    return stop_times


def get_last_detected_stop_time(tracker_id):
    redis_stop_time = cl.zrange(
        get_train_tracker_tracked_stops_key(tracker_id), -1, -1, withscores=True)
    if len(redis_stop_time) > 0:
        return DetectedStopTime.load_from_redis(redis_stop_time[0])
    else:
        return None


def add_report(tracker_id, report):
    is_updated_stop_time = False
    report_id = cl.incr(get_train_tracker_prev_stops_counter_key(tracker_id))
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
            start_stop_time(tracker_id, report_id, stop_id,
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
                tracker_id, report_id, prev_stop_id, stop_time.arrival, prev_timestamp)
            is_updated_stop_time = True
        elif state == DetectorState.states.STOP:
            if detector_state_transition == DetectorState.transitions.NOREPORT_TIMEGAP:
                stop_time = get_last_detected_stop_time(tracker_id)
                print 'NOREPORT_TIMEGAP'
                update_stop_time(tracker_id, report_id, timestamp,
                                 prev_stop_id, None, stop_time.arrival, prev_stop_id, prev_timestamp, True)
                is_updated_stop_time = True
            elif prev_stop_id != stop_id:
                assert False, 'check this code works'
                detector_state.get_prev_stop_data()
                stop_id, timestamp = detector_state.get_oldest_current_state_data(
                    detector_state_transition)
                stop_time = get_last_detected_stop_time(tracker_id)
                end_stop_time_then_start_stop_time(tracker_id,
                                                   report_id,
                                                   stop_id,
                                                   stop_time.arrival,
                                                   timestamp,
                                                   stop_id,
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
