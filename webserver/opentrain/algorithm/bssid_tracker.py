import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
import gtfs.models
from scipy import spatial
import os
import config
import numpy as np
import stops
import shapes
from sklearn.hmm import MultinomialHMM
from utils import *
from collections import deque
from common.ot_utils import meter_distance_to_coord_distance
from redis_intf.client import get_redis_pipeline, get_redis_client
import display_utils
from export_utils import *
from alg_logger import logger
import json
from django.conf import settings

USE_FILE = False

class BSSIDTracker(object):
    def __init__(self) :
        self.wifis_near_no_station = deque(maxlen=100) # limit size to avoid server memory issues
        self.wifis_near_two_or_more_stations = deque(maxlen=100) 
    
    def add(self, report):
        if not report.get_my_loc() or report.loc_ts_delta() > config.stop_discovery_location_timeout_seconds:
            if report.get_my_loc():
                logger.debug('Report %s skipped because of large loc_ts_delta of %d. This is ok if running from a test, as date may have ben changed.' % (str(report), report.loc_ts_delta()))
                return
            else:
                logger.debug('Report %s skipped because it has not location data' % str(report))
                return
        loc = report.get_my_loc()
        wifis = [x for x in report.get_wifi_set_all() if x.SSID == 'S-ISRAEL-RAILWAYS']
        if len(wifis) > 0:
            coords = [loc.lat, loc.lon]
            stop_id_list = stops.all_stops.query_stops(coords, meter_distance_to_coord_distance(config.station_radius_in_meters))
        
        for wifi in wifis:
            if len(stop_id_list) == 1:                
                p = get_redis_pipeline()
                stop_id = stops.all_stops[stop_id_list[0]].id
                p.zincrby("bssid:%s:counters" % (wifi.key), stop_id, 1)
                p.incr("bssid:%s:total" % (wifi.key))
                p.execute()                
            else:
                if len(stop_id_list) == 0:
                    self.wifis_near_no_station.append(wifi)
                else:
                    self.wifis_near_two_or_more_stations.append(wifi)

    def get_stop_id(self, bssid):
        if USE_FILE:
            if file_map.has_key(bssid):
                return file_map[bssid], 1, 1
            else:
                return stops.NOSTOP, 0, 0
        else:
            p = get_redis_pipeline()
            p.zrange("bssid:%s:counters" % (bssid), -1, -1, withscores=True)
            p.get("bssid:%s:total" % (bssid))
            res = p.execute()
            
            counts = [x[1] for x in res[0]]
            stop_id, score = res[0][counts.index(max(counts))]
            stop_id = int(stop_id)
            total = res[1]
            stop_probability = float(score)/float(total)
    
            return stop_id, stop_probability, total


    def get_bssid_stats(self, bssid):
        p = get_redis_pipeline()
        p.zrange("bssid:%s:counters" % (bssid), 0, -1, withscores=True)
        p.get("bssid:%s:total" % (bssid))
        res = p.execute()
        return res[0]

    
    def has_bssid(self, bssid):
        if USE_FILE:
            return file_map.has_key(bssid)
        else:
            cl = get_redis_client()
            return cl.exists("bssid:%s:total" % (bssid))
    
    def has_bssid_high_confidence(self, bssid):
        if USE_FILE:
            return file_map.has_key(bssid)
        else:        
            if not self.has_bssid(bssid):
                return False
            
            _, stop_probability, total = self.get_stop_id(bssid)
            if total < config.stop_discovery_count_thresh:
                return False
    
            if stop_probability < config.stop_discovery_probability_thresh:
                return False
            
            return True
             
    def print_table(self, bssids=None):
        print 'bssid\tcount\tprobability\tstop_id\tname' 
        if bssids is None:
            cl = get_redis_client()
            bssid_keys = cl.keys(pattern='bssid*total')
            bssids = [x.split(":")[1] for x in bssid_keys]
        
        table = []
        for bssid in bssids:
            stop_id, stop_probability, total = self.get_stop_id(bssid)
            if stop_probability > 0.93 and int(total) > 80:
                cur_tuple = (bssid, total, stop_probability, stop_id, stops.all_stops[stop_id].name)
                table.append(cur_tuple)
                print '%s\t%s\t%.2f\t%d\t%s' % cur_tuple
        print json.dumps(table)
       
            
    def get_bssids(self):
        cl = get_redis_client()
        bssid_keys = cl.keys(pattern='bssid*total')
        bssids = [x.split(":")[1] for x in bssid_keys]     
        return bssids
        
def calc_tracker():
    cl = get_redis_client()
    keys = cl.keys(pattern='bssid*')
    if len(keys) > 0:
        cl.delete(*keys)
    tracker = BSSIDTracker()
    reports = analysis.models.Report.objects.filter(wifi_set__SSID = 'S-ISRAEL-RAILWAYS', my_loc__isnull=False).order_by('id')
    reports.prefetch_related('wifi_set', 'my_loc')
    reports = list(set(reports))
    
    for report in reports:
        tracker.add(report)
    tracker.print_table()
    
    return tracker
    
def get_tracker(reset=False):
    if reset:
        bssid_tracker = calc_tracker()
    else:
        bssid_tracker = BSSIDTracker()
    
    return bssid_tracker


def PrintBSSIDReportsOnMap(bssid):
    display_utils.draw_map()
    wifi_reports = analysis.models.SingleWifiReport.objects.filter(key = bssid)
    reports = list(set(x.report for x in wifi_reports))
    
    
    
    
    
    #t = [((x.timestamp - x.get_my_loc().timestamp).total_seconds(), x.get_my_loc().accuracy) for x in reports]
    #t = sorted(t)
    #t = np.array(t)
    #a = [x.get_my_loc().accuracy for x in reports]
    
    #plt.plot(t)
    #plt.plot(a)
    for report in reports:
        if hasattr(report, 'my_loc'):
            plt.scatter(report.my_loc.lon, report.my_loc.lat)
            plt.show
    print 'done'


def print_bssids_report_dates(bssids_lowconf):
    for x in bssids_lowconf:
        wifi_reports = analysis.models.SingleWifiReport.objects.filter(key = x)
        reports = list(set(x.report for x in wifi_reports))
        print x
        for y in reports:
            print y.timestamp    
    return y


def print_bssids_stats(bssids_lowconf):
    for x in bssids_lowconf:
        stat = tracker.get_bssid_stats(x)
        stat = [(stops.all_stops[int(y[0])].name, y[1]) for y in stat]
        print x, stat


def print_bssids_by_stop(bssids_lowconf):
    data = {}
    for x in bssids_lowconf:
        print 'bassid', x
        data[x] = {}
        wifi_reports = analysis.models.SingleWifiReport.objects.filter(key = x)
        reports = list(set(x.report for x in wifi_reports))        
        for report in reports:
            if not report.get_my_loc() or report.loc_ts_delta() > config.stop_discovery_location_timeout_seconds:
                if report.get_my_loc():
                    logger.debug('Report %s skipped because of large loc_ts_delta of %d' % (str(report), report.loc_ts_delta()))
                continue
            loc = report.get_my_loc()
            coords = [loc.lat, loc.lon]
            stop_id_list = stops.all_stops.query_stops(coords, meter_distance_to_coord_distance(config.station_radius_in_meters))
            if stop_id_list:
                if len(stop_id_list) > 1:
                    print 'problem'
                else:
                    if not data[x].has_key(stop_id_list[0]):
                        data[x][stop_id_list[0]] = []
                    data[x][stop_id_list[0]].append((report.timestamp, report.device_id))
        for stop_id in data[x]:
            print stop_id
            for dict_tuple in sorted(data[x][stop_id]):
                print str(dict_tuple[0]), dict_tuple[1]

def load_bssids_from_file():
    import json
    
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'stop_data.json'), 'r') as f:
        stop_data = json.load(f)
   
    del stop_data['netid']    
    data = []
    for bssid in stop_data:
        current_stop_data = stop_data[bssid]
        coords = [current_stop_data['lat'], current_stop_data['lon']]
        stop_id_list = stops.all_stops.query_stops(coords, meter_distance_to_coord_distance(config.station_radius_in_meters))
        if stop_id_list:
            if len(stop_id_list) > 1:
                print 'problem'
            else:
                item = (stops.all_stops[stop_id_list[0]].name, stop_id_list[0], bssid.replace(':','').lower())
                data.append(item)
    #for item in sorted(data):
        #print '%s\t%d\t%s' % (item[0], item[1], item[2])
    bssids = [x[2] for x in data]
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'tracker_stop_data.json'), 'r') as f:
        tracker_stop_data = json.load(f)    
    for data_item in tracker_stop_data:
        if data_item[0] not in bssids:
            data.append((data_item[4], data_item[3], data_item[0]))
                
    return data

tracker = get_tracker(False)
if USE_FILE:
    data = load_bssids_from_file()
    bssids = [x[2] for x in data]
    stop_ids = [x[1] for x in data]
    file_map = dict(zip(bssids, stop_ids))
    

if __name__ == '__main__':
    #tracker.print_table()
    pass

    
    #calc_tracker()    
