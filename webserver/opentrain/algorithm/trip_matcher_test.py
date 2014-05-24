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
from train_tracker import add_report, print_trips, get_trips, get_trusted_trip_or_none

import stops
from common.mock_reports_generator import generate_mock_reports
from analysis.models import SingleWifiReport
from redis_intf.client import get_redis_pipeline, get_redis_client
from stop_detector import DetectedStopTime
from trip_matcher import get_matched_trips
import random
import cProfile

class trip_matcher_test(TestCase):
    

    def test_matcher_on_full_trip(self, trip_id = '010414_00168'):
        detected_stop_times_gtfs, relevant_service_ids, day = self.load_trip_info_for_matcher(trip_id)
            
        trips, time_deviation_in_seconds = get_matched_trips('test_matcher_on_full_trip', detected_stop_times_gtfs,\
                               relevant_service_ids, day)
        matched_trip_id = get_trusted_trip_or_none(trips, time_deviation_in_seconds)        
        self.assertEquals(matched_trip_id, trip_id)
        
    def test_matcher_on_partial_random_trip(self, trip_id = '010414_00168', seeds=[0,1,2,3], stop_counts=[3,4,5]):
        for seed in seeds:
            for stop_count in stop_counts:
                print 'seed =', seed, 'stop_count =', stop_count
                detected_stop_times_gtfs, relevant_service_ids, day = self.load_trip_info_for_matcher(trip_id)
                random.seed(seed)
                subset_inds = sorted(random.sample(xrange(0,len(detected_stop_times_gtfs)),stop_count))
                detected_stop_times_gtfs_subset = [detected_stop_times_gtfs[i] for i in subset_inds]
                trips, time_deviation_in_seconds = get_matched_trips('test_matcher_on_full_trip', detected_stop_times_gtfs,\
                                       relevant_service_ids, day)

                matched_trip_id = get_trusted_trip_or_none(trips, time_deviation_in_seconds)        
                self.assertEquals(matched_trip_id, unicode(trip_id))

    

    def load_trip_info_for_matcher(self, trip_id):
        day = datetime.datetime.strptime(trip_id.split('_')[0], '%d%m%y').date()
        trip = gtfs.models.Trip.objects.filter(trip_id = trip_id)
        stop_times_gtfs = gtfs.models.StopTime.objects.filter(trip = trip_id).order_by('arrival_time')
        detected_stop_times_gtfs = [DetectedStopTime.load_from_gtfs(x, day) for x in stop_times_gtfs]      
        relevant_services = gtfs.models.Service.objects.filter(start_date \
                                                              = day)
        relevant_service_ids = [x[0] for x in relevant_services.all().values_list(\
           'service_id')]
        return detected_stop_times_gtfs, relevant_service_ids, day
        
       
if __name__ == '__main__':
    unittest.main()