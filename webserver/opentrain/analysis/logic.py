import models
import json
import reports.models
import common.ot_utils

from django.conf import settings

def analyze_raw_reports(clean=True):
    if clean:
        delete_all_reports()
    COUNT = 20
    offset = 0
    while True:
        cont = analyze_raw_reports_subset(offset,COUNT)
        offset += COUNT
        if not cont:
            return 
        
def analyze_raw_reports_subset(offset,count):
    items = _collect_items(offset,count)
    if items:
        for item in items:
            try:
                dump_item(item)
            except Exception,e:
                print 'ERROR: Failed to analze item'
                print e
        return True
    return False

from django.db import transaction

@transaction.atomic
def dump_item(item):
    if 'wifi' not in item:
        return None
    wifis = []
    locs = []
    report_dt = common.ot_utils.get_utc_time_from_timestamp(float(item['time'])/1000)
    m = models.Report(device_id=item['device_id'],timestamp=report_dt)
    if models.Report.objects.filter(device_id=item['device_id'],timestamp=report_dt).exists():
        #print 'Repeated report - skipping'
        return None
    m.app_version_name = item.get('app_version_name')
    m.app_version_code = item.get('app_version_code')
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
        if wifi.get('timestamp'):
            ts = common.ot_utils.get_utc_time_from_timestamp(float(wifi['timestamp']) / 1000)
        else:
            ts = None
        wifis.append(models.SingleWifiReport(SSID=wifi['SSID'],
                                             signal=wifi['signal'],
                                             frequency=wifi['frequency'],
                                             key=wifi['key'],
                                             timestamp = ts,
                                             report=m))
    models.SingleWifiReport.objects.bulk_create(wifis)
    models.LocationInfo.objects.bulk_create(locs)
    return m

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
    import algorithm.train_tracker 
    items = json.loads(rr.text)['items']
    reports = []
    for item in items:
        report = dump_item(item)
        if report:
            reports.append(report)
    for report in reports: 
        algorithm.train_tracker.add_report(report) 
    
    
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
        d = dict(device_id=t[0],
                device_date=t[1].isoformat(),
                device_count=t[2])
        result.append(d)
    return result

def get_device_reports(device_id,info):
    qs = models.Report.objects.order_by('id').filter(my_loc__isnull=False,
                                                     id__gte=info['since_id'],
                                                     device_id=device_id)
    if info['stops_only']:
        qs = qs.filter(wifi_set__SSID='S-ISRAEL-RAILWAYS')
    if info['bssid']:
        qs = qs.filter(wifi_set__key=info['bssid'])
    qs = qs.distinct().order_by('id')
    qs = qs.prefetch_related('my_loc','wifi_set')
    info['total_count'] = qs.count()
    qs = qs[info['offset']:info['offset'] + info['limit']]
    result = []
    for obj in qs:
        result.append(obj.to_api_dict(full=info['full']))
    return result
     
def get_current_trips(dt=None):
    import timetable.services
    if not dt:
        dt = common.ot_utils.get_localtime_now()
    current_trips = timetable.services.get_all_trips_in_datetime(dt)
    result = []
    for trip in current_trips:
        trip_dict = trip.to_json_full(with_shapes=False)
        trip_dict['is_live'] = is_live(trip)
        result.append(trip_dict)
    return result
 
def get_trips_location(trip_ids):
    import timetable.services
    result = []
    dt = common.ot_utils.get_localtime_now()
    current_trips = timetable.services.get_trips(trip_ids) 
    for trip in current_trips:
        trip_id = trip.gtfs_trip_id
        exp_shape=timetable.services.get_expected_location(trip, dt)
        res = dict(gtfs_trip_id=trip_id,
                   exp_point = exp_shape)
        cur_loc = get_current_location(trip)
        if cur_loc:
            res['cur_point'] = cur_loc
        result.append(res)                                 
    return result

def get_current_location(trip):
    from redis_intf.client import load_by_key
    return load_by_key('current_trip_id:coords:%s' % (trip.gtfs_trip_id))

def is_live(trip):
    return get_current_location(trip)
    
    





    
        
