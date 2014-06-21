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
from alg_logger import logger
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
import display_utils

def remove_from_redis(device_ids):
    if isinstance(device_ids, basestring):
        device_ids = [device_ids]
    cl = get_redis_client()
    keys = []
    for device_id in device_ids:
        keys.extend(cl.keys(pattern='train_tracker:%s*' % (device_id)))
    if len(keys) > 0:
        cl.delete(*keys)


def get_device_id_reports(device_id):
    qs = analysis.models.Report.objects.filter(device_id=device_id)#,my_loc__isnull=False)
    #qs = qs.filter(timestamp__day=device_date_day,timestamp__month=device_date_month,timestamp__year=device_date_year)
    qs = qs.order_by('timestamp')
    qs = qs.prefetch_related('wifi_set','my_loc')
    #reports = list(qs) takes a long time
    return qs 

class stop_detector_test(TestCase):

    def test_stop_detector_on_mock_trip(self, device_id = 'fake_device_1', trip_id = '010714_00115'):
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

    def _stop_detector_on_real_trip(self, device_id = '1cb87f1e', trip_id = '010414_00168', do_print=False, do_preload_reports=True, set_reports_to_same_weekday_last_week=True, do_show_fig=False):
        remove_from_redis([device_id])
        now = ot_utils.get_localtime_now()
        reports_queryset = get_device_id_reports(device_id)
        tracker_id = device_id
        stops.all_stops.clear
        if do_show_fig:
            display_utils.draw_map()
        
        fps_period_start = time.clock()
        fps_period_length = 100
        if do_preload_reports:
            reports_queryset = list(reports_queryset)
        count = len(reports_queryset) if isinstance(reports_queryset, list) else reports_queryset.count()
        for i in xrange(count):
            if i % fps_period_length == 0:
                elapsed = (time.clock() - fps_period_start)
                if elapsed > 0:
                    logger.debug('%d\t%.1f qps' % (i, fps_period_length/elapsed))
                else:
                    logger.debug('Elapsed time should be positive but is %d' % (elapsed))
                fps_period_start = time.clock()                
            
            report = reports_queryset[i]
            
            if set_reports_to_same_weekday_last_week:
                # fix finding same weekday last week by http://stackoverflow.com/questions/6172782/find-the-friday-of-previous-last-week-in-python
                day_fix = (now.weekday() - report.timestamp.weekday()) % 7
                day = now + datetime.timedelta(days=-day_fix)
                # move day and correct for DST (daylight savings time)
                dst_before = report.get_timestamp_israel_time().dst()
                report.timestamp = report.timestamp.replace(year=day.year, month=day.month, day=day.day)
                dst_after = report.get_timestamp_israel_time().dst()
                report.timestamp -= dst_after-dst_before
            if do_show_fig:
                plt.scatter(report.my_loc.lat, report.my_loc.lon)
                plt.show()
            #print i, ot_utils.get_localtime(report.timestamp)
            stop_times, is_stops_updated = add_report(tracker_id, report)
            if is_stops_updated:
                logger.debug(str(stop_times[-1]))
        
        stop_detector.print_tracked_stop_times(device_id)
        remove_from_redis([device_id])
        print 'done'
        return tracker_id

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

    def test_stop_detector_on_real_trips(self):
        self._stop_detector_on_real_trip(device_id = 'ofer_b3b994f2ff17f4be', trip_id = '010414_00168')
        self._stop_detector_on_real_trip(device_id = 'b37fb3da3c244170', trip_id = '010414_00168')
        self._stop_detector_on_real_trip(device_id = 'ofer_57dd77efa53ebe59', trip_id = '010414_00168')
        self._stop_detector_on_real_trip(device_id = '5e4bcf31fcc4a8d3', trip_id = '010414_00168')
        self._stop_detector_on_real_trip(device_id = '992d69efe920047a', trip_id = '010414_00168')
        self._stop_detector_on_real_trip(device_id = 'ofer_d64213d3f844903d', trip_id = '010414_00168')
        
        #self._stop_detector_on_real_trip(device_id = '71_70d6006f83c00e2a', trip_id = '010414_00168')
            
if __name__ == '__main__':
    unittest.main()
