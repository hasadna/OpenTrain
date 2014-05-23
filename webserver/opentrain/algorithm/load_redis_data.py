# This file contains functions to load data to redis, usually after a redis reset.
import gtfs_datastore
import bssid_tracker

bssid_tracker.calc_tracker()
gtfs_datastore.ReloadRedisGTFSData()