#!/usr/bin/env python

import argparse
import requests

class Replayer(object):

    def __init__(self,gtfs_trip_id,server=None):
        self.gtfs_trip_id = gtfs_trip_id
        self.server = server or 'opentrain.hasanda.org.il'

    def do_get(self,url,params=None):
        final_url = 'http://%s%s' % (self.server, url)
        resp = requests.get(final_url,params=params)
        if not resp.ok:
            with open('/tmp/replay_error.html','w') as fh:
                fh.write(resp.content)
            raise Exception('failed in get %s , written to file:///tmp/replay_error.html' % resp.status_code)
        return resp.json()

    def build_trip(self):
        self.trip_details = self.do_get('/api/1/trips/240814_00146/details/')

    def build_bssid(self):
        self.bssid_to_stop = self.do_get('/api/1/stops/bssids')

    def go(self):
        self.print_header()
        self.build_trip()
        self.build_bssid()



    def print_header(self):
        print '======================================='
        print 'Start replaying'
        print 'Trip id = %s' % self.gtfs_trip_id
        print 'Server = %s' % self.server
        print '======================================='


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='replays trip, for example --gtfs_trip_id 240814_00146')
    parser.add_argument('--gtfs_trip_id',required=True,help='gtfs trip id, for example 240814_00146')
    parser.add_argument('--server')
    ns = parser.parse_args()
    r = Replayer(gtfs_trip_id=ns.gtfs_trip_id,server=ns.server)
    r.go()

def test():
    r = Replayer(gtfs_trip_id='240814_00146') #,server='localhost:8000')
    r.go()
    return r



