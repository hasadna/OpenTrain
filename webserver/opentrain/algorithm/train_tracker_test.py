""" comment 
export DJANGO_SETTINGS_MODULE="opentrain.settings"
"""
import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
#/home/oferb/docs/train_project/OpenTrains/webserver
import timetable.services
import analysis.models
import numpy as np
from scipy import spatial
from alg_logger import logger
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import simplekml
import config
import itertools
import datetime
from unittest import TestCase
import unittest
import time
from display_utils import *
from export_utils import *
import shapes
from train_tracker import add_report, get_trusted_trips, get_train_tracker_trip_delays_ids_list_of_lists_key
import stops
from common.mock_reports_generator import generate_mock_reports
from analysis.models import SingleWifiReport
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import stop_detector_test
import stop_detector
import trip_matcher
import trip_ground_truth
from alg_logger import MessageExcludeFilter


class train_tracker_test(TestCase):

    def track_device(self, device_id, do_print=False, do_preload_reports=True, set_reports_to_same_weekday_last_week=False):
        #device_coords, device_timestamps, device_accuracies_in_meters, device_accuracies_in_coords = get_location_info_from_device_id(device_id)
        now = ot_utils.get_localtime_now()
        reports_queryset = stop_detector_test.get_device_id_reports(device_id)
        tracker_id = device_id
        
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
                
            add_report(report)
            

        #tracker.print_tracked_stop_times()
        #tracker.print_possible_trips()
        trip_delays_ids_list_of_lists = load_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(tracker_id))
        trips = get_trusted_trips(trip_delays_ids_list_of_lists)
        return tracker_id, trips
        
  
    def track_mock_reports(self, reports, tracker_id):
        for i, report in enumerate(reports):
            add_report(report)
        trip_delays_ids_list_of_lists = load_by_key(get_train_tracker_trip_delays_ids_list_of_lists_key(tracker_id))
        trips = get_trusted_trips(trip_delays_ids_list_of_lists)
        return trips
    
    def test_tracker_on_mock_device_multiple_trips(self, device_id = 'fake_device_1', trip_ids = ['010714_00115', '010714_00283'], remove_some_locations=True):
        self.test_tracker_on_mock_device(device_id, trip_ids, remove_some_locations)
        
    def test_tracker_on_mock_device(self, device_id = 'fake_device_1', trip_ids = ['010714_00115'], remove_some_locations=True):
        if not isinstance(trip_ids, list):
            trip_ids = [trip_ids]
        tracker_id = device_id
        stop_detector_test.remove_from_redis(tracker_id)
        reports = []
        for trip_id in trip_ids:
            day = datetime.datetime.strptime(trip_id.split('_')[0], '%d%m%y')
            now = ot_utils.get_localtime_now() # we want to get the correct timezone so we take it from get_localtime_now()
            day = now.replace(year=day.year, month=day.month, day=day.day)
            trip_reports = generate_mock_reports(device_id=device_id, trip_id=trip_id, nostop_percent=0.05, day=day)
            reports += trip_reports
            
        if remove_some_locations:
            for report in reports[::2]:
                del report.my_loc_mock
            logger.addFilter(MessageExcludeFilter('skipped because it has not location data'))
        
        matched_trips = self.track_mock_reports(reports, tracker_id)
        for matched_trip in matched_trips:
            timetable.services.get_trip(matched_trip).print_stoptimes()
        self.assertEquals(len(matched_trips), len(trip_ids))        
        self.assertEquals(sorted(matched_trips), sorted(trip_ids))
        stop_detector_test.remove_from_redis(tracker_id)        
        
    def test_tracker_on_real_devices(self):    
        device_ids = []
        trip_suffixes_list = []
        device_ids.append('ofer_995357870c491cad')
        device_ids.append('ofer_207fabab5f381476')
        for device_id in device_ids:
            trip_suffixes_list.append(trip_ground_truth.data[device_id])
        
        stop_detector_test.remove_from_redis(device_ids)
        
        for i in xrange(len(device_ids)):
            device_id = device_ids[i] 
            trip_suffixes = trip_suffixes_list[i]
            tracker_id, trips = self.track_device(device_id, do_preload_reports=True)
            for trip_id in trips:
                timetable.services.print_trip_stop_times(trip_id)
            stop_detector.print_tracked_stop_times(device_id)
            
            self.assertEquals(len(trips), len(trip_suffixes))
            for trip_suffix in trip_suffixes:
                self.assertTrue(self.is_trip_in_list(trips, trip_suffix))
      
        stop_detector_test.remove_from_redis(device_ids)
        
  

    def is_trip_in_list(self, trips, trip_id_end):
        return len([x for x in trips if x.endswith(trip_id_end)]) > 0


        
if __name__ == '__main__':
    unittest.main()