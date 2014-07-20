import numpy as np
from redis import WatchError
from redis_intf.client import (get_redis_pipeline,
                               get_redis_client,
                               load_by_key,
                               save_by_key)
import bssid_tracker
import config
import json
import stops
from alg_logger import logger
from common import ot_utils
from utils import enum

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
        arrival = ot_utils.get_localtime(gtfs_stop_time.exp_arrival)
        departure = ot_utils.get_localtime(gtfs_stop_time.exp_departure)
        return DetectedStopTime(gtfs_stop_time.stop.gtfs_stop_id, arrival, departure)

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
        logger.info('init detector_state')
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
        logger.info('key={}, value={}'.format(key, value))
        save_by_key(key, value, cl=p)

    states = enum(INITIAL='initial', NOSTOP='nostop',
                  STOP='stop', UNKNOWN_STOP='unknown_stop')
    transitions = enum(NORMAL='normal', NOREPORT_TIMEGAP='noreport_timegap')


def _get_report_data(report):
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
            logger.warning('No stop for bssids: %s' %
                         ','.join([x.key for x in wifis]))
            stop_id = None
            state = DetectorState.states.UNKNOWN_STOP
    else:
        stop_id = stops.NOSTOP_ID
        state = DetectorState.states.NOSTOP

    timestamp = report.get_timestamp_israel_time()
    return state, stop_id, timestamp


def _start_stop_time(tracker_id, stop_id, arrival_time, prev_stop_time=None, is_report_timegap=False):
    logger.info('Calling _start_stop_time. is_report_timegap={}'.format(is_report_timegap))
    _update_stop_time(tracker_id, arrival_time, stop_id, None, prev_stop_time, is_report_timegap)
    

def _end_stop_time(tracker_id, stop_id, arrival_time, departure_time, prev_stop_time=None):
    logger.info('Calling _end_stop_time.')
    _update_stop_time(tracker_id, arrival_time, stop_id, departure_time, prev_stop_time)


def _update_stop_time(tracker_id, arrival_timestamp, stop_id, departure_time, prev_stop_time, is_report_timegap=False):
    if not prev_stop_time:
        prev_stop_time = get_last_detected_stop_time(tracker_id)
    if prev_stop_time and prev_stop_time.stop_id == stop_id and not is_report_timegap:
        arrival_timestamp = prev_stop_time.arrival

    arrival_unix_timestamp = int(ot_utils.dt_time_to_unix_time(arrival_timestamp))
    departure_time = departure_time.isoformat() if departure_time else None
    stop_id_and_departure_time = json.dumps((stop_id, departure_time))

    p.zremrangebyscore(get_train_tracker_tracked_stop_times_key(
        tracker_id), arrival_unix_timestamp, arrival_unix_timestamp)
    p.zadd(get_train_tracker_tracked_stop_times_key(tracker_id),
           arrival_unix_timestamp, stop_id_and_departure_time)


def get_detected_stop_times(tracker_id, last_n=0):
    stop_times_redis = cl.zrange(get_train_tracker_tracked_stop_times_key(
        tracker_id), last_n*-1, -1, withscores=True)
    stop_times = []
    for cur in stop_times_redis:
        stop_times.append(DetectedStopTime.load_from_redis(cur))
    return stop_times


def get_last_detected_stop_time(tracker_id):
    stop_times = get_detected_stop_times(tracker_id, last_n=1)
    return stop_times[0] if len(stop_times) > 0 else None


def print_tracked_stop_times(tracker_id):
    stop_times = get_detected_stop_times(tracker_id)
    for stop_time in stop_times:
        print stop_time


def add_report(tracker_id, report):
    logger.info('adding report={}'.format(report))
    is_updated_stop_time = False
    report_id = cl.incr(get_train_tracker_report_id_key(tracker_id))
    updated_report_id_key = get_train_tracker_updated_report_id_key(
        tracker_id)
    # We try to update a report only if no report was updated with a more recent 
    # report_id than us. If one was updated, we don't update at all. 
    # This is done using check-and-set (see http://redis.io/topics/transactions)
    done = False
    while not done:
        logger.info('in while loop')
        p.watch(updated_report_id_key)
        updated_report_id = load_by_key(updated_report_id_key)
        logger.info('updated_report_id={}, report_id={}'.format(updated_report_id, report_id))
        if not updated_report_id or updated_report_id < report_id:
            try:
                p.multi()
                is_updated_stop_time = _try_add_report(tracker_id, report)
                p.set(updated_report_id_key, report_id)
                p.execute()
                done = True
            except WatchError:
                logger.info('WatchError: {}'.format(WatchError))
                done = False
                p.unwatch()
        else:
            logger.info('Report not used because of report_id.')
            done = True
            p.unwatch()
    logger.info('is_updated_stop_time={}, done={}'.format(is_updated_stop_time, done))
    return is_updated_stop_time and done


def _try_add_report(tracker_id, report):
    logger.info('tracker_id={} report={}'.format(tracker_id, report))
    is_updated_stop_time = False
    
    logger.info('fetching detector_state.')
    detector_state = DetectorState(tracker_id)
    logger.info('fetched detector_state.')
    prev_state, prev_stop_id, prev_timestamp = detector_state.get_current()
    logger.info('prev_state={} prev_stop_id={} prev_timestamp={}'.format(prev_state, prev_stop_id, prev_timestamp))
    # new report is older than last report:
    if prev_timestamp and report.timestamp < prev_timestamp:
        logger.warning('New report is older than last report. New report timestamp={}. Last report timestamp={}'.format(report.timestamp, prev_timestamp))
        return None

    state, stop_id, timestamp = _get_report_data(report)
    logger.info('state={} stop_id={} timestamp={}'.format(state, stop_id, timestamp))
    if stop_id == stops.NOSTOP_ID: #XXX
        logger.info('stop_id == stops.NOSTOP_ID, so returning None')
        return None
    if prev_timestamp and timestamp - prev_timestamp > config.no_report_timegap:
        detector_state_transition = DetectorState.transitions.NOREPORT_TIMEGAP
    else:
        detector_state_transition = DetectorState.transitions.NORMAL

    logger.info('Setting detector state: state={} stop_id={} timestamp={}'.format(state, stop_id, timestamp))
    detector_state.set_current(state, stop_id, timestamp)
    if prev_state in [DetectorState.states.INITIAL, DetectorState.states.NOSTOP]:
        if state == DetectorState.states.NOSTOP:
            logger.info('passing big if statement')
            pass
        elif state == DetectorState.states.STOP:
            _start_stop_time(tracker_id, stop_id, timestamp)
            is_updated_stop_time = True
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            logger.info('passing big if statement')
            pass
    elif prev_state == DetectorState.states.STOP:
        if state == DetectorState.states.NOSTOP:
            stop_time = get_last_detected_stop_time(tracker_id)
            _end_stop_time(
                tracker_id, prev_stop_id, stop_time.arrival, prev_timestamp, stop_time)
            is_updated_stop_time = True
        elif state == DetectorState.states.STOP:
            if detector_state_transition == DetectorState.transitions.NOREPORT_TIMEGAP:
                stop_time = get_last_detected_stop_time(tracker_id)
                print 'NOREPORT_TIMEGAP'
                _end_stop_time(tracker_id, prev_stop_id, stop_time.arrival, prev_timestamp, stop_time)
                _start_stop_time(tracker_id, prev_stop_id, timestamp, stop_time, True)
                is_updated_stop_time = True
            elif prev_stop_id != stop_id:
                stop_time = get_last_detected_stop_time(tracker_id)
                _end_stop_time(tracker_id, prev_stop_id, stop_time.arrival, prev_timestamp, stop_time)
                _start_stop_time(tracker_id, stop_id, timestamp, stop_time)                
                is_updated_stop_time = True
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            logger.info('passing big if statement')
            pass
    elif prev_state == DetectorState.states.UNKNOWN_STOP:
        if state == DetectorState.states.NOSTOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            logger.info('passing big if statement')
            pass
        elif state == DetectorState.states.STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            logger.info('passing big if statement')
            pass
        elif state == DetectorState.states.UNKNOWN_STOP:
            # TODO: Add handling of UNKNOWN_STOP stop_time
            logger.info('passing big if statement')
            pass

    return is_updated_stop_time


cl = get_redis_client()
p = get_redis_pipeline()
