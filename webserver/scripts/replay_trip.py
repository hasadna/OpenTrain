#!/usr/bin/env python

import argparse
import requests
import collections
import dateutil.parser


class Replayer(object):
    def __init__(self, gtfs_trip_id, device_id,server=None):
        self.gtfs_trip_id = gtfs_trip_id
        self.server = server or 'opentrain.hasadna.org.il'
        if device_id.startswith('dummy'):
            device_id = 'dummy_%s' % device_id
        self.device_id = device_id

    def do_get(self, url, params=None):
        final_url = 'http://%s%s' % (self.server, url)
        resp = requests.get(final_url, params=params)
        if not resp.ok:
            with open('/tmp/replay_error.html', 'w') as fh:
                fh.write(resp.content)
            raise Exception('failed in get %s , written to file:///tmp/replay_error.html' % resp.status_code)
        return resp.json()

    def build_trip(self):
        self.trip_details = self.do_get('/api/1/trips/240814_00146/details/')

    def build_bssid(self):
        self.bssid_to_stop = self.do_get('/api/1/stops/bssids')
        self.stop_to_bssids = collections.defaultdict(list)
        for bssid, info in self.bssid_to_stop.iteritems():
            self.stop_to_bssids[info['gtfs_stop_id']].append(bssid)

    def make_item(self,bssid,ssid,report_time,loc_time=None,latlon=None):
        result = {'app_version_code': 18,
                  'app_version_name': '0.7.6',
                  'device_id': self.device_id,
                  'time': self.time_to_ms(report_time),
                  'wifi': [{'SSID': ssid,
                            'frequency': 2412,
                            'key': bssid,
                            'signal': -71}]}
        if latlon:
            result['location_api'] = {'accuracy': 10,
                                   'lat': latlon[0],
                                   'long': latlon[1],
                                   'provider': 'fused',
                                   'time': self.time_to_ms(loc_time)},
        return result

    def send_stop_report(self, stop_time):
        bssids = self.stop_to_bssids[stop_time['stop']['gtfs_stop_id']]
        if not bssids:
            print 'No bssids for %s' % (stop_time['stop']['gtfs_stop_id'])
            return
        arrival_time = dateutil.parser.parse(stop_time['exp_arrival'])
        item = self.make_item(bssid=bssids[0],
                              ssid='S-ISRAEL-RAILWAYS',
                              report_time=arrival_time)

    def send_reports(self):
        stop_times = self.trip_details['stop_times']
        for stop_time in stop_times:
            self.send_stop_report(stop_time)


    def go(self):
        self.print_header()
        self.build_trip()
        self.build_bssid()
        self.send_reports()


    def print_header(self):
        print '======================================='
        print 'Start replaying'
        print 'Trip id = %s' % self.gtfs_trip_id
        print 'Server = %s' % self.server
        print '======================================='


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='replays trip, for example --gtfs_trip_id 240814_00146')
    parser.add_argument('--gtfs_trip_id', required=True, help='gtfs trip id, for example 240814_00146')
    parser.add_argument('--server')
    parser.add_argument('--device_id',required=True)
    ns = parser.parse_args()
    r = Replayer(gtfs_trip_id=ns.gtfs_trip_id, server=ns.server,device_id=ns.device_id)
    r.go()


def test():
    r = Replayer(gtfs_trip_id='240814_00146',device_id='eran')  # ,server='localhost:8000')
    r.go()
    return r



