from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import analysis.utils

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ( 
         make_option('--gps',
            action='store_true',
            dest='gps',
            default=False,
            help='Show gps info'),
        make_option('--wifi',
            action='store_true',
            dest='wifi',
            default=False,
            help='Show wifi info'))
        
    help = 'Show device info'
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Must give device-id-partial-name")
        
        device_pat = args[0]
        device_ids = analysis.utils.find_device_ids(device_pat)
        if len(device_ids) == 0:
            raise CommandError('Did not found any device id matching %s' % (device_pat))
        if len(device_ids) > 1:
            raise CommandError('Found more than one device id matching %s:\n%s' % (device_pat,'\n'.join(device_ids)))
        self.device_id = device_ids[0]
        if options['gps']:
            self.print_gps_info()
        if options['wifi']:
            self.print_wifi_info()
    
    def print_title(self,msg):
        self.stdout.write('=' * (len(msg)))
        self.stdout.write(msg)
        self.stdout.write('=' * (len(msg)))
        
    def print_gps_info(self):
        self.print_title('GPS REPORT for device %s' % self.device_id)
        
        reports = analysis.utils.get_reports(self.device_id)
        reports_with_loc = [r for r in reports if hasattr(r,'my_loc')]
        r = None
        self.stdout.write('# of reports = %s' % (len(reports)))
        self.stdout.write('# of reports with loc = %s' % (len(reports_with_loc)))
        threshold = 1000
        path = '%10s %10s %10s %10s %10s %10s'
        pat = '%10s %10s %10.2f %10.2f %10s %10.2f'
        self.stdout.write(path % ('INDEX','ID','DIST PREV','DIST NEXT','ACCURACY','TS DIFF'))
        for idx in xrange(1,len(reports_with_loc)-1):
            r_prev = reports_with_loc[idx-1]
            r_cur = reports_with_loc[idx]
            r_next = reports_with_loc[idx+1]
            dist_prev = analysis.utils.find_reports_dist(r_prev, r_cur)
            dist_next = analysis.utils.find_reports_dist(r_cur, r_next)
            ts_diff = (r_cur.timestamp - r_cur.my_loc.timestamp).total_seconds()
            if dist_prev > threshold:
                self.stdout.write(pat % (idx,r_cur.id,dist_prev,dist_next,r_cur.my_loc.accuracy,ts_diff))
        
    def print_wifi_info(self):
        self.print_title('WIFI analysis for device %s' % self.device_id)
        reports = analysis.utils.get_reports(self.device_id)
        stations = []
        for report in reports:
            if report.is_station():
                stations.append(report)
        print 'Reports : %s' % len(reports)
        print 'Reports in station: %s' % len(stations)
            
                
                          
                          
