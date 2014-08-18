""" comment 
export DJANGO_SETTINGS_MODULE="opentrain.settings"
"""
import os
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
os.environ['DJANGO_SETTINGS_MODULE'] = 'opentrain.settings'
import mock_trip
import unittest
from unittest import TestCase
import common.mock_reports_generator

class stop_detector_test(TestCase):

    def test_mock_trip_correctly_matched(self, device_id_base='fake_sys_', trip_id='210714_00234', server='opentrain.hasadna.org.il'):
        device_id = common.ot_utils.get_localtime_now().strftime('{}_%Y%m%d_%H%M'.format(device_id_base))
        reports = common.mock_reports_generator.generate_mock_reports(device_id, trip_id, nostop_percent=0.05)
        print 'trip_id = %s' % (trip_id)
        print 'device_id = %s' % (device_id)
        print 'server = %s' % (server)
        mock_trip.send_reports(reports, server)
        self.assertEquals(1, 1)
        print 'done'
        
    #def test_real_trip_correctly_matched(


if __name__ == '__main__':
    unittest.main()
