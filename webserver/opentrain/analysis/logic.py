import models
import json
import reports.models
import common.ot_utils

def analyze_raw_reports(clean=True):
    if clean:
        delete_all_reports()
    COUNT = 100
    offset = 0
    while True:
        cont = analyze_raw_reports_subset(offset,COUNT)
        offset += COUNT
        if not cont:
            return 
    
def analyze_raw_reports_subset(offset,count):
    items = _collect_items(offset,count)
    if items:
        dump_items(items)
        return True
    return False

from django.db import transaction

@transaction.atomic
def dump_items(items):
    wifis = []
    locs = []
    for (idx,item) in enumerate(items):
        if idx % 100 == 0:
            print '%d/%d' % (idx,len(items))
        if 'wifi' in item.keys():
            report_dt = common.ot_utils.get_utc_time_from_timestamp(float(item['time'])/1000)
            m = models.Report(device_id=item['device_id'],timestamp=report_dt)
            m.save()
            item_loc = item.get('location_api')
            if item_loc:
                loc = models.LocationInfo(report=m,
                                          lat=item_loc['lat'],
                                          lon=item_loc['long'],
                                          provider=item_loc['provider'],
                                          timestamp = common.ot_utils.get_utc_time_from_timestamp(float(item_loc['time'])/1000),
                                          accuracy = item_loc['accuracy'])
                locs.append(loc)
            for wifi in item['wifi']:
                wifis.append(models.SingleWifiReport(SSID=wifi['SSID'],
                                 signal=wifi['signal'],
                                 frequency=wifi['frequency'],
                                 key=wifi['key'],
                                 report=m))
    print 'Saving all dependant objects'
    models.SingleWifiReport.objects.bulk_create(wifis)
    models.LocationInfo.objects.bulk_create(locs)

def delete_all_reports():
    common.ot_utils.delete_from_model(models.SingleWifiReport)
    common.ot_utils.delete_from_model(models.LocationInfo)
    common.ot_utils.delete_from_model(models.Report)
    
def _collect_items(offset,count):
    all_reports_count = reports.models.RawReport.objects.count()
    print '*** offset = %d count = %d all_reports_count = %d' % (offset,count,all_reports_count)
    all_reports = reports.models.RawReport.objects.all().order_by('id')[offset:offset+count]
    result = []
    for rj in all_reports:
        items = json.loads(rj.text)['items']
        result.extend(items)
    return result

def analyze_single_raw_report(rr):
    items = json.loads(rr.text)['items']
    dump_items(items)
    
## DEVICES SUMMAY ##    
    
def get_devices_summary():
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("""
        SELECT device_id,MIN(DATE(timestamp)) as device_date,
        COUNT(*) from analysis_report 
        GROUP BY device_id 
        ORDER BY device_date
    """)
    tuples = cursor.fetchall()
    result = []
    for t in tuples:
        d = DeviceObject(device_id=t[0],
                         device_date=t[1],
                         device_count=t[2])
        result.append(d)
    return result

class DeviceObject(object):
    def __init__(self,device_id=None,device_date=None,device_count=None):
        self.device_id = device_id
        self.device_date = device_date
        self.device_count = device_count

    
## CUR TRIPS ##
    
class TripLocationObject(object):
    def __init__(self,trip_id,cur_point,exp_point,ts):
        self.trip_id = trip_id
        self.cur_point = cur_point
        self.exp_point = exp_point
        self.ts = ts 
def get_current_trips():
    pass


    






    
        
