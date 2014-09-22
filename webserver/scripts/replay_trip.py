#!/usr/bin/env python

import argparse
import requests
import collections
from datetime import timedelta
import dateutil.parser
import random
import json
import datetime
import pytz
import time
import os
import logging

DIST_TO_STOP = 300
HALF_MIN = timedelta(seconds=30)
TWO_SECS = timedelta(seconds=2)


class ShapeInfo(object):
    def __init__(self, shape_idx, stop_idx=None, prev_stop_idx=None, dist=None):
        if stop_idx is not None:
            assert dist, 'Dist cannot be None if stop_idx is given'
        else:
            assert prev_stop_idx is not None
        self.stop_idx = stop_idx
        self.dist = dist
        self.prev_stop_idx = prev_stop_idx
        self.time = None
        self.shape_idx = shape_idx

    def __unicode__(self):
        if self.stop_idx is not None:
            return "#{self.shape_idx} @{self.time} S = {self.stop_idx} dist = {self.dist:.1f}".format(self=self)
        else:
            return "#{self.shape_idx} @{self.time} PS = {self.prev_stop_idx}".format(self=self)

    def __repr__(self):
        return self.__unicode__()

    def __nonzero__(self):
        return self.stop_idx is not None


class Replayer(object):
    def __init__(self, gtfs_trip_id, device_id=None, batch_size=None,server=None,delay=None,post_server=None,test=False):
        if test:
            self.gtfs_trip_id = '020914_00158'
        else:
            self.gtfs_trip_id = gtfs_trip_id
        self.server = server or 'opentrain.hasadna.org.il'
        self.post_server = post_server or self.server
        self.device_id = device_id
        if device_id is None:
            self.device_id = '%s_%s' % (os.environ['USER'],datetime.datetime.utcnow().strftime('%Y%m%d%H%M'))
        self.batch_size = batch_size
        self.delay = delay

    def do_get(self, url, params=None):
        final_url = 'http://%s%s' % (self.server, url)
        resp = requests.get(final_url, params=params)
        if not resp.ok:
            with open('/tmp/replay_error.html', 'w') as fh:
                fh.write(resp.content)
            raise Exception('failed in get %s , written to file:///tmp/replay_error.html' % resp.status_code)
        return resp.json()

    def do_post(self, url, data=None,headers=None):
        final_url = 'http://%s%s' % (self.post_server, url)
        #print url,data
        resp = requests.post(final_url, data=data,headers=headers)
        if not resp.ok:
            with open('/tmp/replay_error.html', 'w') as fh:
                fh.write(resp.content)
            raise Exception('failed in post %s , written to file:///tmp/replay_error.html' % resp.status_code)
        return resp.json()
        #return dict(cur_gtfs_trip_id=123456)

    def calc_distance(self, latlon1, latlon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        from math import radians, cos, sin, asin, sqrt
        # convert decimal degrees to radians
        lat1, lon1 = latlon1
        lat2, lon2 = latlon2
        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = 6367 * c
        return km * 1000


    def build_trip(self):
        self.trip_details = self.do_get('/api/1/trips/%s/details/' % self.gtfs_trip_id)
        stop_times = self.trip_details['stop_times']
        shapes = self.trip_details['shapes']
        self.shape_infos = [None] * len(shapes)
        last_stop_idx = -1
        for shape_idx, shape in enumerate(shapes):
            dists = [self.calc_distance(shape, stop_time['stop']['latlon']) for stop_time in stop_times]
            val, idx = min((val, idx) for (idx, val) in enumerate(dists))
            if val < DIST_TO_STOP:
                self.shape_infos[shape_idx] = ShapeInfo(shape_idx, stop_idx=idx, dist=val)
                last_stop_idx = idx
            else:
                assert last_stop_idx >= 0
                self.shape_infos[shape_idx] = ShapeInfo(shape_idx, stop_idx=None, prev_stop_idx=last_stop_idx)

        print '# of stops = %s' % (len(stop_times))
        # for stop in stop_times:
        #    print stop
        self.check_shapes()
        self.compute_shape_times()
        self.check_shape_times()

    def check_shape_times(self):
        print 'Checking times...'
        assert len(self.shape_infos) == len(self.trip_details['shapes'])
        sis = self.shape_infos
        for idx in xrange(1, len(sis)):
            assert sis[idx].time > sis[idx - 1].time, '%s %s' % (sis[idx - 1], sis[idx])

    def split_time_to_shapes(self, sis, start_time, stop_time):
        assert len(sis) > 0, 'sis cannot be empty'
        seconds = (stop_time - start_time).total_seconds()
        assert seconds > 0, 'time diff must be positive'
        sis[0].time = start_time.replace(microsecond=0)
        if len(sis) == 1:
            return
        step = seconds / (len(sis) - 1)
        assert step > 1, 'step must be > 1'
        steps = 0
        for si in sis[1:]:
            steps += step
            si.time = (start_time + timedelta(seconds=steps)).replace(microsecond=0)
        assert abs((sis[-1].time - stop_time).total_seconds()) < 1.0

    def compute_shape_times(self):
        stop_times = self.trip_details['stop_times']
        for idx, st in enumerate(stop_times):
            sis = [si for si in self.shape_infos if si.stop_idx == idx]
            assert len(sis) > 1, 'no shape infos for stop_idx = %s' % idx
            exp_arrival = dateutil.parser.parse(st['exp_arrival'])
            exp_departure = dateutil.parser.parse(st['exp_departure'])
            self.split_time_to_shapes(sis, exp_arrival - HALF_MIN, exp_arrival + HALF_MIN)
            if idx + 1 < len(stop_times):
                exp_arrival_next = dateutil.parser.parse(stop_times[idx + 1]['exp_arrival'])
                sis = [si for si in self.shape_infos if si.prev_stop_idx == idx]
                assert len(sis) > 1, 'no shape infos for prev_stop_idx = %s' % idx
                time1 = exp_departure + HALF_MIN + TWO_SECS
                time2 = exp_arrival_next - HALF_MIN - TWO_SECS
                self.split_time_to_shapes(sis, time1, time2)

    def check_shapes(self):
        print 'Checking shapes'
        stop_times = self.trip_details['stop_times']
        last_was_none = False
        all_stop_idxes = []
        for idx, si in enumerate(self.shape_infos):
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
            else:
                assert si.prev_stop_idx == all_stop_idxes[-1]
                # print '%s : %s %.1f' % (idx,stop_idx,stop_dist)
            if idx == 0 and not si:
                raise Exception('first idx must have dist')
            if idx == len(self.shape_infos) - 1 and not si:
                raise Exception('last idx must have dist')
            last_was_none = False if si else True

        if all_stop_idxes != range(0, len(stop_times)):
            print all_stop_idxes
            print range(0, len(stop_times))
            raise Exception('not all stop idxes were covered')

    def build_bssid(self):
        self.bssid_to_stop = self.do_get('/api/1/stops/bssids')
        self.stop_to_bssids = collections.defaultdict(list)
        for bssid, info in self.bssid_to_stop.iteritems():
            self.stop_to_bssids[info['gtfs_stop_id']].append(bssid)

    def time_to_ms(self,dt):
        epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
        delta = dt - epoch
        return int(delta.total_seconds() * 1000)


    def get_shape_item(self, si):
        if si.stop_idx:
            ssid = 'S-ISRAEL-RAILWAYS'
            gtfs_stop_id = self.trip_details['stop_times'][si.stop_idx]['stop']['gtfs_stop_id']
            bssids = self.stop_to_bssids[gtfs_stop_id]
            if len(bssids) == 0:
                print 'No BSSIDS found for gtfs_stop_id = %s' % gtfs_stop_id
                bssid = '123456'
            else:
                bssid = random.choice(bssids)
        else:
            bssid = "b4c79982bd90"
            ssid = "ISRAEL-RAILWAYS"

        result = {'app_version_code': 18,
                  'app_version_name': '0.7.6',
                  'device_id': self.device_id,
                  'time': self.time_to_ms(si.time),
                  'wifi': [{'SSID': ssid,
                            'frequency': 2412,
                            'key': bssid,
                            'signal': -71}]}
        latlon = self.trip_details['shapes'][si.shape_idx]
        loc_api = {'accuracy': 10,
                  'lat': latlon[0],
                  'long': latlon[1],
                  'provider': 'fused',
                  'time': self.time_to_ms(si.time)}
        result['location_api'] = loc_api
        return result

    def send_reports(self):
        sis = self.shape_infos
        batches=[sis[x:x+self.batch_size] for x in xrange(0, len(sis), self.batch_size)]
        for batch in batches:
            self.send_batch(batch)

    def send_batch(self,sis):
        items = [self.get_shape_item(si) for si in sis]
        data = dict(items=items)
        while True:
            try:
                result = self.do_post('/reports/add/',data=json.dumps(data),headers={'content-type' : 'application/json'})
                break
            except Exception,e:
                print 'Failed in post - retry in 1 second'
                time.sleep(1)
        desc_list = []
        for si in sis:
            if si.stop_idx is not None:
                desc = 'STOP-%s' % si.stop_idx
            elif si.prev_stop_idx is not None:
                desc = 'AFTER-%s' % si.prev_stop_idx
            else:
                assert False
            if desc not in desc_list:
                desc_list.append(desc)
        items_desc = ' ,'.join(desc_list)
        print 'Send %s items of type %s. result = %s' % (len(items),items_desc,result['cur_gtfs_trip_id'])
        time.sleep(self.delay)

    def go(self):
        self.print_header()
        self.build_trip()
        self.build_bssid()
        self.send_reports()


    def print_header(self):
        print '======================================='
        print 'Start replaying'
        print 'Trip id = %s' % self.gtfs_trip_id
        print 'device id = %s' % self.device_id
        print 'Server = %s' % self.server
        print 'Delay = %s' % self.delay
        print 'Batch Size = %s' % self.batch_size
        print '======================================='


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='replays trip, for example --gtfs_trip_id 020914_00158')
    parser.add_argument('--gtfs_trip_id', help='gtfs trip id, for example 020914_00158')
    parser.add_argument('--server')
    parser.add_argument('--post_server')
    parser.add_argument('--device_id',help='fake device id, if none with take $USER with timestamp')
    parser.add_argument('--batch_size',default=20,type=int,help='number of items in one POST call')
    parser.add_argument('--delay',default=0.1,type=float,help='delay between calls, default is 0.1')
    parser.add_argument('--test',action='store_true')
    ns = parser.parse_args()
    r = Replayer(**vars(ns))
    r.print_header()
    r.go()





