# This file contains functions to load data to redis, usually after a redis reset.
import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
import gtfs_datastore
import bssid_tracker

def load():
    #bssid_tracker.calc_tracker()
    gtfs_datastore.ReloadRedisGTFSData()
    
if __name__ == '__main__':
    load()
