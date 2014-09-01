#!/usr/bin/env python

import argparse
import requests
import collections
import dateutil.parser

DIST_TO_STOP = 300


class ShapeInfo(object):
    def __init__(self,stop_idx=None,dist=None):
        if stop_idx is not None:
            assert dist,'Dist cannot be None if stop_idx is given'
        self.stop_idx = stop_idx
        self.dist = dist

    def __nonzero__(self):
        return self.stop_idx is not None

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

    def calc_distance(self,latlon1,latlon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        from math import radians, cos, sin, asin, sqrt
        # convert decimal degrees to radians
        lat1,lon1 = latlon1
        lat2,lon2 = latlon2
        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6367 * c
        return km * 1000


    def build_trip(self):
        self.trip_details = self.do_get('/api/1/trips/%s/details/'  % self.gtfs_trip_id)
        stop_times = self.trip_details['stop_times']
        shapes = self.trip_details['shapes']
        self.shape_infos = [None] * len(shapes)
        for shape_idx,shape in enumerate(shapes):
            dists = [self.calc_distance(shape,stop_time['stop']['latlon']) for stop_time in stop_times]
            val, idx = min((val, idx) for (idx, val) in enumerate(dists))
            if val < DIST_TO_STOP:
                self.shape_infos[shape_idx] = ShapeInfo(stop_idx=idx,dist=val)
            else:
                self.shape_infos[shape_idx] = ShapeInfo(stop_idx=None)

        print '# of stops = %s' % (len(stop_times))
        #for stop in stop_times:
        #    print stop
        self.check_shapes()
        #self.compute_shape_times()


    def check_shapes(self):
        print 'Checking shapes'
        stop_times = self.trip_details['stop_times']
        last_was_none = False
        all_stop_idxes = []
        for idx,si in enumerate(self.shape_infos):
            if si:
                if all_stop_idxes:
                    last_stop_idx = all_stop_idxes[-1]
                else:
                    last_stop_idx = -1
                if si.stop_idx == last_stop_idx:
                    if last_was_none:
                        raise Exception('Illegal dist - same idx with null between for idx = %s' % idx)
                elif si.stop_idx != last_stop_idx + 1:
                    raise Exception('Illegal dist - should be consecutive for idx = %s' % idx)
                else:
                    all_stop_idxes.append(si.stop_idx)
                #print '%s : %s %.1f' % (idx,stop_idx,stop_dist)
            if idx == 0 and not si:
                raise Exception('first idx must have dist')
            if idx == len(self.shape_infos) - 1 and not si:
                raise Exception('last idx must have dist')
            last_was_none = False if si else True

        if all_stop_idxes != range(0,len(stop_times)):
            print all_stop_idxes
            print range(0,len(stop_times))
            raise Exception('not all stop idxes were covered')


        

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

    def send_reports(self):
        stop_times = self.trip_details['stop_times']
        for stop_time in stop_times:
            self.send_stop_report(stop_time)


    def go(self):
        self.print_header()
        self.build_trip()
        #self.build_bssid()
        #self.send_reports()


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
    r = Replayer(gtfs_trip_id='020914_00158',device_id='eran')  # ,server='localhost:8000')
    r.go()
    return r



