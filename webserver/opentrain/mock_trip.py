#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
import sys
import json
import requests
import argparse
import time
import common.mock_reports_generator


def send_reports(reports, server, delay=0):
    url = 'http://%s/reports/add/' % (server)
    for idx,report in enumerate(reports):
        rr = common.mock_reports_generator.raw_report_from_report(report)
        headers = {'content-type':'application/json'}
        body = json.dumps(rr)
        resp = requests.post(url,headers=headers,data=body)
        if not resp.ok:
            print 'failed with: ' + resp.content[0:100]
            print 'full log in /tmp/error.html'
            with open('/tmp/error.html','w') as fh:
                fh.write(resp.content)
            sys.exit(1)
        time.sleep(delay)
        print 'Sent %d / %d so far' % (idx + 1, len(reports))

if __name__ == '__main__':
    default_device_id = common.ot_utils.get_localtime_now().strftime('test_%Y%m%d_%H%M')
    parser = argparse.ArgumentParser(description='mock trip id')
    parser.add_argument('--server',type=str,required=True)
    parser.add_argument('--device_id',type=str,default=default_device_id)
    parser.add_argument('--trip_id',type=str,required=True)
    parser.add_argument('--delay',type=float,default=0.0)
    
    ns = parser.parse_args()
    reports = common.mock_reports_generator.generate_mock_reports(ns.device_id, ns.trip_id, nostop_percent=0.05)
    print 'Going to send %d reports' % (len(reports))
    
    print 'trip_id = %s' % (ns.trip_id)
    print 'device_id = %s' % (ns.device_id)
    print 'server = %s' % (ns.server)
    print 'delay = %s' % (ns.delay)
    print 'website url = http://opentrain.hasadna.org.il/analysis/device-reports/?device_id={}'.format(ns.device_id)    
    
    send_reports(reports, ns.server, ns.delay)
    
