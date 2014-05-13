from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import gtfs.utils
import common.ot_utils

class Command(BaseCommand):
    args = '<device-id-partial-name>'
    help = 'Analyze gps location of given report, can be given partially'
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Must give device-id-partial-name")
        
        import analysis.utils
        device_pat = args[0]
        device_ids = analysis.utils.find_device_ids(device_pat)
        if len(device_ids) == 0:
            raise CommandError('Did not found any device id matching %s' % (device_pat))
        if len(device_ids) > 1:
            raise CommandError('Found more than one device id matching %s:\n%s' % (device_pat,'\n'.join(device_ids)))
        device_id = device_ids[0]
        msg = 'GPS REPORT for device %s' % device_id
        self.stdout.write('=' * (len(msg)))
        self.stdout.write(msg)
        self.stdout.write('=' * (len(msg)))

                          
                          
