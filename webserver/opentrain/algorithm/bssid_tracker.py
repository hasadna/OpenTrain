import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
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
import common.ot_utils as ot_utils
from redis_intf.client import get_redis_pipeline, get_redis_client
import display_utils
from export_utils import *
from alg_logger import logger
import json
from django.conf import settings
import math
import common.mock_reports_generator

USE_FILE = True
FAKE_BSSID_PREFIX = common.mock_reports_generator.FAKE_BSSID_PREFIX

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
        
        if USE_FILE and not bssid.startswith(FAKE_BSSID_PREFIX):
            if file_map.has_key(bssid):
                return file_map[bssid], 1, 1
            else:
                logger.warn('Unknown bssid: %s' % bssid)
                return stops.NOSTOP_ID, 0, 0
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
        if USE_FILE and not bssid.startswith(FAKE_BSSID_PREFIX):
            return file_map.has_key(bssid)
        else:
            cl = get_redis_client()
            return cl.exists("bssid:%s:total" % (bssid))
    
    def has_bssid_high_confidence(self, bssid):
        if USE_FILE and not bssid.startswith(FAKE_BSSID_PREFIX):
            result = file_map.has_key(bssid)
            if not result:
                logger.warn('Unknown bssid: %s' % bssid)
            return result
        else:        
            if not self.has_bssid(bssid):
                logger.warn('Unknown bssid: %s' % bssid)
                return False
            
            _, stop_probability, total = self.get_stop_id(bssid)
            if total < config.stop_discovery_count_thresh:
                return False
    
            if stop_probability < config.stop_discovery_probability_thresh:
                return False
            
            return True
    
    def get_bssids():
        cl = get_redis_client()
        bssid_keys = cl.keys(pattern='bssid*total')
        bssids = [x.split(":")[1] for x in bssid_keys]  
        return bssids
    
    def print_table(self, bssids=None):
        print 'bssid\tcount\tprobability\tstop_id\tname' 
        if bssids is None:
            bssids = self.get_bssids()
        
        table = []
        bssids = [x for x in bssids if 'FAKE' not in x]
        for bssid in bssids:
            stop_id, stop_probability, total = self.get_stop_id(bssid)
            #if stop_probability >= config.stop_discovery_probability_thresh and int(total) >= config.stop_discovery_count_thresh:
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
    reports = analysis.models.Report.objects.filter(wifi_set__SSID = 'S-ISRAEL-RAILWAYS', my_loc__isnull=False).order_by('device_id', 'timestamp')
    reports.prefetch_related('wifi_set', 'my_loc')
    reports = list(set(reports))
    
    ignore_timestamp = reports[0].timestamp
    ignore_devices_timestamps = []
    prev_loc = None
    prev_device_id = None
    for i, report in enumerate(reports):
        if i % 1000 == 0:
            print i
        lat = report.get_my_loc().lat if report.get_my_loc() else None
        lon = report.get_my_loc().lon if report.get_my_loc() else None
        if prev_loc and report.get_my_loc() and prev_device_id == report.device_id:
            dist = math.sqrt(math.pow(lat - prev_loc.lat,2) + math.pow(lon - prev_loc.lon,2))*110101.0
        else:
            dist = -1
        if dist > 200:
            ignore_timestamp = report.timestamp
            ignore_devices_timestamps.append((ignore_timestamp, report.device_id))
        prev_loc = report.get_my_loc()
        prev_device_id = report.device_id
        
        
    ignore_devices = set(x[1] for x in ignore_devices_timestamps)
    devices = set([x.device_id for x in reports])
    good_devices = devices - ignore_devices
    non_test_devices = [x for x in devices if 'test' not in devices]
    for x in non_test_devices:
        print x
    for i, report in enumerate(reports):
        if i % 1000 == 0:
            print i
            tracker.print_table()
        if report.device_id not in ignore_devices:
            tracker.add(report)
        else:
            print 'Ignoring report'
    tracker.print_table()
    
    return tracker
    
def get_tracker(reset=False):
    if reset:
        bssid_tracker = calc_tracker()
    else:
        bssid_tracker = BSSIDTracker()
    
    return bssid_tracker


def PrintBSSIDReportsOnMap(bssid):
    #display_utils.draw_map()
    wifi_reports = analysis.models.SingleWifiReport.objects.filter(key = bssid)
    reports = list(set(x.report for x in wifi_reports))
    
    #t = [((x.timestamp - x.get_my_loc().timestamp).total_seconds(), x.get_my_loc().accuracy) for x in reports]
    #t = sorted(t)
    #t = np.array(t)
    #a = [x.get_my_loc().accuracy for x in reports]
    ts = sorted([x.timestamp for x in reports])
    import common.ot_utils as ot_utils
    sorted_reports = sorted(zip(ts, reports))
    sorted_reports = [x[1] for x in sorted_reports]
    for x in sorted_reports:
        print x.id, x, ot_utils.get_localtime(x.timestamp), x.my_loc.lat, x.my_loc.lon
    
    ot_utils.get_localtime(ts[0])
    ot_utils.get_localtime(ts[-1])
    
    #plt.plot(t)
    #plt.plot(a)
    for i, report in enumerate(reports):
        print i
        if hasattr(report, 'my_loc'):
            plt.scatter(report.my_loc.lon, report.my_loc.lat, s=10)
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


def print_bssids_stats(bssids):
    for x in bssids:
        stat = tracker.get_bssid_stats(x)
        stat = [(stops.all_stops[int(y[0])].name, y[1]) for y in stat]
        print x, stat


def print_bssids_by_stop(bssids):
    data = {}
    for x in bssids:
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

def load_bssids_from_json_file():
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

def load_bssids_from_manual_map_file():
    data = []
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'data', 'manual_bssid_map.txt'), 'r') as f:
        content = f.readlines()          
    for line in content:
        line = line.strip('\n')
        if line and line[0] != '#':
            bssid = line.split(' ', 1)[0]
            rest = line.split(' ', 1)[1]
            stop_id = int(rest.split(' ', 1)[0])
            name = rest.split(' ', 1)[1]
            data.append((name, stop_id, bssid))
    
    return data
            

def get_bssid_data_for_app():
  bssids = tracker.get_bssids()
  high_conf_bssids = [x for x in bssids if tracker.has_bssid_high_confidence(x)]
  result = dict()
  for bssid in high_conf_bssids:
      (stop_id,prob,total) = tracker.get_stop_id(x)
      entry = {
        'stop_id': stop_id,
        'probability' : prob,
        'total' : total
      }
      result[bssid] = entry
  return result

tracker = get_tracker(False)
if USE_FILE:
    data = load_bssids_from_manual_map_file()
    bssids = [x[2] for x in data]
    stop_ids = [x[1] for x in data]
    file_map = dict(zip(bssids, stop_ids))

def print_trip_story(device_id):
    bssid_map = {}
    has_unmapped_bssid = False
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'data', 'manual_bssid_map.txt'), 'r') as f:
        content = f.readlines()          
    for line in content:
        line = line.strip('\n')
        if line and line[0] != '#':
            bssid_map[line.split(' ', 1)[0]] = line.split(' ', 1)[1]
    reports3 = analysis.models.Report.objects.filter(device_id = device_id).order_by('timestamp')
    prev_loc = None
    prev_has_bssid = False
    for report in reports3:
        #has_bssid = bssid in [x.key for x in report.get_wifi_set_all()]
        has_bssid = 'S-ISRAEL-RAILWAYS' in [x.SSID for x in report.get_wifi_set_all()]
        if prev_has_bssid != has_bssid:
            if has_bssid:
                start_time = ot_utils.get_localtime(report.timestamp)
            else:
                print start_time.date(), start_time.strftime("%H:%M:%S"), ot_utils.get_localtime(report.timestamp).strftime("%H:%M:%S"), report.device_id, has_bssid
        stop_bssids = [x.key for x in report.get_wifi_set_all() if x.SSID == 'S-ISRAEL-RAILWAYS'] 
        if not all(x in bssid_map for x in stop_bssids):
            has_unmapped_bssid = True
        stop_bssids = [bssid_map[x] if x in bssid_map else x for x in stop_bssids]
        if stop_bssids:
            print ot_utils.get_localtime(report.timestamp).strftime("%H:%M:%S"), sorted(stop_bssids)
        #print ot_utils.get_localtime(report.timestamp), report.device_id, bssid, has_bssid, lat, lon, int(dist)
        #print report.timestamp, ot_utils.get_localtime(report.timestamp), report.device_id, bssid, has_bssid, lat, lon, int(dist)
        prev_loc = report.get_my_loc()
        prev_has_bssid = has_bssid 
    if has_unmapped_bssid:
        print 'HAS UNMAPPED BSSID!!!'
    else:
        print 'All bssids mapped'

if __name__ == '__main__':
    #PrintBSSIDReportsOnMap('b4c799a3dee0') #'b4c79982a110')
    #bssid = 'b4c799a3ddd0'
    #wifi_reports = analysis.models.SingleWifiReport.objects.filter(key = bssid)
    #reports = list(set(x.report for x in wifi_reports))    
    ##tracker.print_table()
    #device_ids = sorted(set([(x.timestamp.date(), x.device_id) for x in reports]))
    #for x in device_ids:
        #print x
    
    #reports2 = list(set(x.report for x in wifi_reports if x.report.device_id == '887e38a68fba876b'))    
    #for x in reports2:
        #print x
    
    
    #device_id = '940e3161c577f921'
    #print_trip_story(device_id)


    #reports = analysis.models.Report.objects.all()
    #device_ids = sorted(set([(x.timestamp.date(), x.device_id) for x in reports]))
    #for x in device_ids:
        #count = len(analysis.models.Report.objects.filter(device_id = x[1]))
        #if not ('test' in x[1] or 'windows' in x[1]) and count > 100:
            #continue
        #else:
            #print x, count
            
    #with open(os.path.join(settings.BASE_DIR, 'algorithm', 'data', 'device_ids_to_keep.txt'), 'r') as f:
        #content = f.readlines()
    #for line in content:
        #print line[line.index("u'")+2:line.index("')")]
    
    #import reports
    #rr = reports.models.RawReport.objects.all().order_by('saved_at')
    #for x in rr:
        #print x.id, x.saved_at, x.text
    #r = reports.models.RawReport.objects.filter(saved_at=datetime(2014, 06, 22)).order_by('saved_at')
    pass
    
    #calc_tracker()    
