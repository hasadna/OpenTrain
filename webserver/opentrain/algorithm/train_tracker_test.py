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
from train_tracker import add_report, print_trips, get_trusted_trips, get_train_tracker_trip_delays_ids_list_of_lists_key
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

class train_tracker_test(TestCase):

    def track_device(self, device_id, do_print=False, do_preload_reports=True, set_reports_to_same_weekday_last_week=True):
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
    
    def teXXXst_tracker_on_mock_device_multiple_trips(self, device_id = 'fake_device_1', trip_ids = ['010414_00100', '010414_00168'], remove_some_locations=True):
        self.test_tracker_on_mock_device(device_id, trip_ids, remove_some_locations)
        
    def teXXXst_tracker_on_mock_device(self, device_id = 'fake_device_1', trip_ids = ['010414_00168'], remove_some_locations=True):
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

        for report in reports[::2]:
            del report.my_loc_mock
        
        matched_trips = self.track_mock_reports(reports, tracker_id)
        for matched_trip in matched_trips:
            gtfs.models.Trip.objects.filter(trip_id = matched_trip)[0].print_stoptimes()
        self.assertEquals(len(matched_trips), len(trip_ids))        
        self.assertEquals(sorted(matched_trips), sorted(trip_ids))
        stop_detector_test.remove_from_redis(tracker_id)        
        
    def test_tracker_on_real_devices(self):    
        device_ids = []
        trip_suffixes_list = []
        device_ids.append('1cb87f1e')# Udi's trip  
        trip_suffixes_list.append(['_00073'])
        device_ids.append('91b251f8')
        trip_suffixes_list.append(['_00152'])        
        device_ids.append('eran_ec8d0d5fd1a16aed')
        trip_suffixes_list.append(['_00046'])              
        device_ids.append('ofer_57656382027dc9c8')
        trip_suffixes_list.append(['_00281'])
        device_ids.append('eran_63479c43eb54ff1f')
        trip_suffixes_list.append(['_00050'])
        #device_ids.append('ed918429baaf8ab8')
        #trip_suffixes_list.append(['_00086'])
        device_ids.append('5dc40476ad438414')
        trip_suffixes_list.append(['_00164'])

        #device_ids.append('2dfc74b71c91677b')
        #trip_suffixes_list.append(['_00956']) # wrongly takes _00685 as second trip. What is correct trip?
        #device_ids.append('iocean_323b5911306012a9')
        #trip_suffixes_list.append(['_00124'])        

        device_ids.append('eran_b7fa2ccec8c127d2')        
        trip_suffixes_list.append(['_00050'])
        #device_ids.append('3c70f9b11f28734b')        
        #trip_suffixes_list.append(['_00956', '_00279'])

        #device_ids.append('0c89639c69c4caf1') # this one can't find the evening trip
        #trip_suffixes_list.append(['_00956', '_00279'])
        ##device_ids.append('0756bb390dabe025') # this one merges stops from different trips        
        ##trip_suffixes_list.append(['_00956', '_00227'])

        device_ids.append('eran_ec8d0d5fd1a16aed')        
        trip_suffixes_list.append(['_00046'])        
        #device_ids.append('0297cb91eaf724cd')        
        #trip_suffixes_list.append(['_00956'])        

        ##device_ids.append('d9e77fb9c6c851f4') # only tel aviv stations detected, but by map should be more     
        ##trip_suffixes_list.append(['_00956'])
        ##device_ids.append('871d8773d36a2b8f') # only tel aviv stations detected, but by map should be more     
        ##trip_suffixes_list.append(['_00956'])

        #device_ids.append('eran_63479c43eb54ff1f')        
        #trip_suffixes_list.append(['_00050'])
        #device_ids.append('ofer_57656382027dc9c8')        
        #trip_suffixes_list.append(['_00281'])

        ##device_ids.append('ofer_a7700dd1b90dea4c') # download db
        ##trip_suffixes_list.append(['_00281'])
        ##device_ids.append('Amit_81db2ecaa94d5377') # download db
        ##trip_suffixes_list.append(['_00281'])  
        ##device_ids.append('eran_5060bdab5d871850') # download db
        ##trip_suffixes_list.append(['_00281']) 
        ##device_ids.append('ofer_9d7d84b96a97b156') # download db
        ##trip_suffixes_list.append(['_00281'])        
        ##device_ids.append('eran_d57316d7c8610535') # download db
        ##trip_suffixes_list.append(['_00281'])
        ##device_ids.append('ofer_e402a16800ea3cc9') # download db
        ##trip_suffixes_list.append(['_00281'])


        
        stop_detector_test.remove_from_redis(device_ids)
        
        for i in xrange(len(device_ids)):
            device_id = device_ids[i] 
            trip_suffixes = trip_suffixes_list[i]
            tracker_id, trips = self.track_device(device_id, do_preload_reports=True)
            for trip_id in trips:
                trip_matcher.print_trip(trip_id)
            stop_detector.print_tracked_stop_times(device_id)
            
            self.assertEquals(len(trips), len(trip_suffixes))
            for trip_suffix in trip_suffixes:
                self.assertTrue(self.is_trip_in_list(trips, trip_suffix))
      
        stop_detector_test.remove_from_redis(device_ids)
        
  

    def is_trip_in_list(self, trips, trip_id_end):
        return len([x for x in trips if x.endswith(trip_id_end)]) > 0


        
if __name__ == '__main__':
    unittest.main()