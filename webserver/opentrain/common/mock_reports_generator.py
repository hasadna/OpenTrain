""" comment 
export DJANGO_SETTINGS_MODULE="opentrain.settings"
"""
import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
#/home/oferb/docs/train_project/OpenTrains/webserver
import timetable.services
import analysis.models
import numpy as np
import itertools
import datetime
import algorithm.shapes as shapes
import algorithm.stops as stops
import ot_utils

FAKE_BSSID_PREFIX = 'FAKE'

def generate_mock_reports(device_id='fake_device_1', trip_id='010714_00115', day=None, from_stop_id=None, to_stop_id=None, nostop_percent=0.2, station_radius_in_meters=300):
    trip = timetable.services.get_trip(trip_id)
    # TODO(oferb): 
    stop_times = trip.get_stop_times()
    if not day:
        day = ot_utils.get_localtime_now()
        print 'WARNING: Note that there may be time zone issues'
    else:
        day = ot_utils.get_localtime(day)
    
    # filter stop times by from_stop_id and to_stop_id:
    trip_stop_ids = [x.stop.gtfs_stop_id for x in stop_times]
    from_stop_ind = 0
    if from_stop_id:
        from_stop_ind = trip_stop_ids.index(from_stop_id)
    to_stop_ind = None
    if to_stop_id:
        to_stop_ind = trip_stop_ids.index(to_stop_id)+1
    stop_times = stop_times[from_stop_ind:to_stop_ind]
    trip_stop_ids = set([x.stop.gtfs_stop_id for x in stop_times])

    # get coords:
    coords = trip.get_points()
    #coords = np.array(coords)
    accuracies = np.ones((len(coords),1))*ot_utils.meter_distance_to_coord_distance(station_radius_in_meters)
    
    # map shape-points to stops:
    stop_ids = stops.all_stops.query_stops(coords, accuracies)
    
    # filter out stops not in trip:
    stop_ids_uniques = set(stop_ids)
    if len(trip_stop_ids - stop_ids_uniques) > 0:
        unfound_stops = trip_stop_ids - stop_ids_uniques
        print('Warning: these stops were not found in gtfs shape: %s' % (unfound_stops))
    stops_not_in_trip = stop_ids_uniques - trip_stop_ids - set([stops.NOSTOP_ID])
    stop_ids = [x if x not in stops_not_in_trip else stops.NOSTOP_ID for x in stop_ids]

    # strip nostops from start and end
    while len(stop_ids) > 0 and stop_ids[0] == stops.NOSTOP_ID:
        del stop_ids[0]
    while len(stop_ids) > 0 and stop_ids[-1] == stops.NOSTOP_ID:
        del stop_ids[-1]    

    # remove nostop reports according to nostop_percent:
    nostop_inds = [i for i in xrange(len(stop_ids)) if stop_ids[i] == stops.NOSTOP_ID]
    keep_inds = [i for i in xrange(len(stop_ids)) if stop_ids[i] != stops.NOSTOP_ID]
    nostop_inds = nostop_inds[::int(1/nostop_percent)]
    keep_inds.extend(nostop_inds)
    stop_ids = [stop_ids[i] for i in xrange(len(stop_ids)) if i in keep_inds]
    coords = [coords[i] for i in xrange(len(coords)) if i in keep_inds]


    stop_id_to_stop_time_dict = {}
    for stop_time in stop_times:
        stop_id_to_stop_time_dict[stop_time.stop.gtfs_stop_id] = stop_time
    
    from itertools import groupby
    stop_id_groups = []
    stop_id_group_lens = []
    stop_id_unique_keys = []
    for k, g in groupby(stop_ids):
        g = list(g)
        stop_id_groups.append(g)      # Store group iterator as a list
        stop_id_group_lens.append(len(g))
        stop_id_unique_keys.append(k)     

    # create reports with corresponding location and wifi:
    reports = []
    last_stop = None
    prev_stop_id = None
    stop_index = -1
    counter = -1
    group_index = -1
    for coord, stop_id, i in zip(coords, stop_ids, xrange(len(stop_ids))):
        if stop_id != prev_stop_id:
            counter = -1
            group_index += 1
            if stop_id != stops.NOSTOP_ID:
                stop_index += 1
                interval_start = stop_times[stop_index].exp_arrival
                interval_end = stop_times[stop_index].exp_departure
                #print '%s %s' % (stop_id, stop_times[stop_index].stop.stop_id)
            else:
                interval_start = stop_times[stop_index].exp_departure
                interval_end = stop_times[stop_index+1].exp_arrival
        #print i, stop_id       
        counter += 1
        interval_ratio = float(counter)/stop_id_group_lens[group_index]
        timestamp = interval_start + datetime.timedelta(seconds=interval_ratio*(interval_end-interval_start).total_seconds())
        #timestamp = day.replace(hour=timestamp/3600, minute=timestamp % 3600 / 60, second=timestamp % 60 / 60)
        
        report = analysis.models.Report()
        reports.append(report)
        loc = analysis.models.LocationInfo()
        #loc.report = report
        loc.accuracy = 0.1
        loc.lat = coord[0]
        loc.lon = coord[1]
        loc.provider = 'mock'
        loc.timestamp = timestamp
        report.my_loc_mock = loc
        
        wifi_report_train = analysis.models.SingleWifiReport()
        wifi_report_train.report = report
        wifi_report_train.SSID = TRAIN_SSID
        wifi_report_train.frequency = -13
        wifi_report_train.signal = 13
        wifi_report_train.key = '%s_%s' % (FAKE_BSSID_PREFIX, device_id)    
        report.wifi_set_mock = [wifi_report_train]
    
        if stop_id != stops.NOSTOP_ID:
            wifi_report_station = analysis.models.SingleWifiReport()
            wifi_report_station.report = report
            wifi_report_station.SSID = STATION_SSID
            wifi_report_station.frequency = 12
            wifi_report_station.signal = -12
            wifi_report_station.key = 'FAKE_%s' % (stop_id)
            report.wifi_set_mock.append(wifi_report_station)
        
        report.device_id = device_id
        report.timestamp = timestamp
        report.created = timestamp
        
        report.device_id = device_id
        
        prev_stop_id = stop_id
    
    return reports

#general
STATION_SSID = 'S-ISRAEL-RAILWAYS'
TRAIN_SSID = 'ISRAEL-RAILWAYS'


def raw_report_from_report(report):
    rr = dict()
    items = []
    fake_timestamp = int(ot_utils.dt_time_to_unix_time(report.timestamp)*1000)
    item = dict()
    item['app_version_name'] = u'0.7.6'
    item['app_version_code'] = 18
    item['time'] = fake_timestamp
    item['device_id'] = report.device_id
    wifis = []
    for wifi in report.get_wifi_set_all():
        w = dict()
        w['signal'] = wifi.signal
        w['frequency'] = wifi.frequency
        w['SSID'] = wifi.SSID
        w['key'] = wifi.key
        wifis.append(w)
    item['wifi'] = wifis
    loc = report.get_my_loc()
    if loc:
        l = dict()
        l['bearing'] = 0
        l['altitude'] = 0
        l['provider'] = loc.provider
        l['long'] = loc.lon
        l['lat'] = loc.lat
        l['time'] = fake_timestamp
        l['accuracy'] = loc.accuracy
        item['location_api'] = l
    items.append(item)
    rr['items'] = items
    return rr


if __name__ == '__main__':
    reports = generate_mock_reports(nostop_percent=0.05)
    print len(reports)
