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
import train_tracker_test


def run_tracker_on_trips_without_ground_truth(device_ids=None):    
    trip_suffixes_list = []
    if not device_ids:
        device_ids = [x for x in trip_ground_truth.data if not trip_ground_truth.data[x]]
    
    stop_detector_test.remove_from_redis(device_ids)
    
    for i in xrange(len(device_ids)):
        device_id = device_ids[i] 
        tracker_id, trips = train_tracker_test.track_device(device_id, do_preload_reports=True)
        print 'DEVICE_ID=%s' % device_id
        for trip_id in trips:
            timetable.services.print_trip_stop_times(trip_id)
        stop_detector.print_tracked_stop_times(device_id)
        
    stop_detector_test.remove_from_redis(device_ids)
    
if __name__ == '__main__':
    logger.addFilter(MessageExcludeFilter('saving disabled!!!'))
    run_tracker_on_trips_without_ground_truth(['ofer_df0106ed1d770799'])    