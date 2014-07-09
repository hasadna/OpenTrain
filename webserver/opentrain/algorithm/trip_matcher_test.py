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
from train_tracker import add_report, get_trusted_trips

import stops
from common.mock_reports_generator import generate_mock_reports
from analysis.models import SingleWifiReport
from redis_intf.client import get_redis_pipeline, get_redis_client
from stop_detector import DetectedStopTime
from trip_matcher import get_matched_trips
import random
import cProfile

class trip_matcher_test(TestCase):
    

    def test_matcher_on_full_trip(self, trip_id = '010714_00115'):
        detected_stop_times_gtfs, day = self.load_trip_info_for_matcher(trip_id)
            
        trip_delays_ids_list_of_lists = get_matched_trips('test_matcher_on_full_trip', detected_stop_times_gtfs,\
                               day)
        self.assertEquals(len(trip_delays_ids_list_of_lists), 1)        
        matched_trip_ids = get_trusted_trips(trip_delays_ids_list_of_lists)
        self.assertEquals(matched_trip_ids[0], trip_id)

    def test_matcher_on_trip_set(self, trip_ids = ['010714_00283', '010714_00115']):
        detected_stop_times_gtfs_all = []
        for trip_id in trip_ids:
            detected_stop_times_gtfs, day = self.load_trip_info_for_matcher(trip_id)
            detected_stop_times_gtfs_all += detected_stop_times_gtfs
            
        trip_delays_ids_list_of_lists = get_matched_trips('test_matcher_on_full_trip', detected_stop_times_gtfs_all,\
                               day)
        
        self.assertEquals(len(trip_delays_ids_list_of_lists), 2)        
        matched_trip_ids = sorted(get_trusted_trips(trip_delays_ids_list_of_lists))
        self.assertEquals(matched_trip_ids, sorted(trip_ids))
        
        
    def test_matcher_on_partial_random_trip(self, trip_id = '010714_00115', seeds=[0,1,2,3], stop_counts=[3,4,5]):
        for seed in seeds:
            for stop_count in stop_counts:
                print 'seed =', seed, 'stop_count =', stop_count
                detected_stop_times_gtfs, day = self.load_trip_info_for_matcher(trip_id)
                random.seed(seed)
                subset_inds = sorted(random.sample(xrange(0,len(detected_stop_times_gtfs)),stop_count))
                detected_stop_times_gtfs_subset = [detected_stop_times_gtfs[i] for i in subset_inds]
                trip_delays_ids_list_of_lists = get_matched_trips('test_matcher_on_full_trip', detected_stop_times_gtfs,\
                                       day)


                self.assertEquals(len(trip_delays_ids_list_of_lists), 1)        
                matched_trip_ids = get_trusted_trips(trip_delays_ids_list_of_lists)
                self.assertEquals(matched_trip_ids[0], unicode(trip_id))

    def load_trip_info_for_matcher(self, trip_id):
        day = datetime.datetime.strptime(trip_id.split('_')[0], '%d%m%y').date()
        trip = timetable.services.get_trip(trip_id)
        stop_times_gtfs = trip.get_stop_times()
        detected_stop_times_gtfs = [DetectedStopTime.load_from_gtfs(x, day) for x in stop_times_gtfs]      
        return detected_stop_times_gtfs, day
        
       
if __name__ == '__main__':
    unittest.main()