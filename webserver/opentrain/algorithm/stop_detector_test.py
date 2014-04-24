""" comment 
export DJANGO_SETTINGS_MODULE="opentrain.settings"
"""
import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
#/home/oferb/docs/train_project/OpenTrains/webserver
import gtfs.models
import analysis.models
import numpy as np
from scipy import spatial
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import config
import itertools
import datetime
from unittest import TestCase
import unittest
import time
from display_utils import *
from export_utils import *
from train_tracker import print_trips, get_trips, get_trusted_trip_or_none

import stops
from common.mock_reports_generator import generate_mock_reports
from analysis.models import SingleWifiReport
from redis_intf.client import get_redis_pipeline, get_redis_client
from stop_detector import DetectedStopTime
from trip_matcher import get_matched_trips
import random
import cProfile
from stop_detector import add_report
import stop_detector


def remove_from_redis(device_ids):
    if isinstance(device_ids, basestring):
        device_ids = [device_ids]
    cl = get_redis_client()
    keys = []
    for device_id in device_ids:
        keys.extend(cl.keys(pattern='train_tracker:%s*' % (device_id)))
    if len(keys) > 0:
        cl.delete(*keys)

class train_tracker_test(TestCase):

    def test_stop_detector_on_mock_trip(self, device_id = 'fake_device_1', trip_id = '010414_00168'):
        remove_from_redis([device_id])
        day = datetime.datetime.strptime(trip_id.split('_')[0], '%d%m%y')
        now = ot_utils.get_localtime_now() # we want to get the correct timezone so we take it from get_localtime_now()
        day = now.replace(year=day.year, month=day.month, day=day.day)
        reports = generate_mock_reports(device_id=device_id, trip_id=trip_id, nostop_percent=0.05, day=day)
        tracker_id = device_id
        for i, report in enumerate(reports):
            add_report(tracker_id, report=report)
            if (i % 100) == 0:
                print i
                stop_detector.print_tracked_stop_times(tracker_id)
            
        self.evaluate_detected_stop_times(tracker_id, trip_id)
        remove_from_redis([device_id])
        print 'done'

    def test_stop_detector_on_real_trip(self, device_id = 'fake_device_1', trip_id = '010414_00168'):
            remove_from_redis([device_id])
            day = datetime.datetime.strptime(trip_id.split('_')[0], '%d%m%y')
            now = ot_utils.get_localtime_now() # we want to get the correct timezone so we take it from get_localtime_now()
            day = now.replace(year=day.year, month=day.month, day=day.day)
            reports = generate_mock_reports(device_id=device_id, trip_id=trip_id, nostop_percent=0.05, day=day)
            tracker_id = device_id
            for i, report in enumerate(reports):
                add_report(tracker_id, report=report)
                if (i % 100) == 0:
                    print i
                    stop_detector.print_tracked_stop_times(tracker_id)
                
            self.evaluate_detected_stop_times(tracker_id, trip_id)
            remove_from_redis([device_id])
            print 'done'

    def evaluate_detected_stop_times(self, device_id, trip_id):
        detected_stop_times = stop_detector.get_detected_stop_times(tracker_id=device_id)
        gtfs_stop_times = gtfs.models.StopTime.objects.filter(trip = trip_id).order_by('arrival_time').values_list('stop', 'arrival_time', 'departure_time')
        acceptible_time_delta = 60 # one minute
        for detected_stop_time, gtfs_stop_time in zip(detected_stop_times, gtfs_stop_times):
            gtfs_stop_id = gtfs_stop_time[0]
            gtfs_arrival = gtfs_stop_time[1]
            gtfs_departure = gtfs_stop_time[2]
            msg = str(detected_stop_time)
            detected_arrival = ot_utils.datetime_to_db_time(detected_stop_time.arrival)
            self.assertAlmostEquals(detected_arrival, gtfs_arrival, msg=msg, delta=acceptible_time_delta)   
            is_last_detected_stop = detected_stop_time == detected_stop_times[-1]
            # allow for last stop to not have departure
            if detected_stop_time.departure or not is_last_detected_stop:
                detected_departure = ot_utils.datetime_to_db_time(detected_stop_time.departure)
                self.assertAlmostEquals(detected_departure, gtfs_departure, msg=msg, delta=acceptible_time_delta)
            
if __name__ == '__main__':
    unittest.main()