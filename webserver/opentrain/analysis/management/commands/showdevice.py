from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import analysis.utils

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ( 
         make_option('--gpsglitch',
            action='store_true',
            dest='gpsglitch',
            default=False,
            help='Show gps glitches'),
        make_option('--gpsdist',
            action='store_true',
            dest='gpsdist',
            default=False,
            help='Show gps distribution'),
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
        self.reports = analysis.utils.get_reports(self.device_id)
        self.reports_with_loc = [r for r in self.reports if hasattr(r,'my_loc')] 
        self.print_title('General info for %s' % (self.device_id))
        self.stdout.write('# of reports = %s' % (len(self.reports)))
        self.stdout.write('# of reports with loc = %s' % (len(self.reports_with_loc)))
        self.stdout.write('From: %s' % (self.reports[0].timestamp.replace(microsecond=0)))
        self.stdout.write('To: %s' % (self.reports[-1].timestamp.replace(microsecond=0)))
        if options['gpsglitch']:
            self.print_gps_info()
        if options['wifi']:
            self.print_wifi_info()
        if options['gpsdist']:
            self.print_gps_dist()
            
    
    def print_title(self,msg):
        self.stdout.write('=' * (len(msg)))
        self.stdout.write(msg)
        self.stdout.write('=' * (len(msg)))
        
    def print_gps_info(self):
        self.print_title('GPS glitches')
        self.stdout.write('# of reports with loc = %s' % (len(self.reports_with_loc)))
        threshold = 1000
        path = '%10s %10s %10s %10s %10s %10s'
        pat = '%10s %10s %10.2f %10.2f %10s %10.2f'
        self.stdout.write(path % ('INDEX','ID','DIST PREV','DIST NEXT','ACCURACY','TS DIFF'))
        for idx in xrange(1,len(self.reports_with_loc)-1):
            r_prev = self.reports_with_loc[idx-1]
            r_cur = self.reports_with_loc[idx]
            r_next = self.reports_with_loc[idx+1]
            dist_prev = analysis.utils.find_reports_dist(r_prev, r_cur)
            dist_next = analysis.utils.find_reports_dist(r_cur, r_next)
            ts_diff = (r_cur.timestamp - r_cur.my_loc.timestamp).total_seconds()
            if dist_prev > threshold:
                self.stdout.write(pat % (idx,r_cur.id,dist_prev,dist_next,r_cur.my_loc.accuracy,ts_diff))
                
    def print_gps_dist(self):
        import collections
        self.print_title('GPS Distribution')
        buckets = (5,10,50,100,500,1000,5000,10000,50000,100000)
        result = collections.defaultdict(int)
        for bucket in buckets:
            result[bucket] = 0
        for idx in xrange(1,len(self.reports_with_loc)-1):
            r_prev = self.reports_with_loc[idx-1]
            r_cur = self.reports_with_loc[idx]
            dist_prev = analysis.utils.find_reports_dist(r_prev, r_cur)
            found = False
            #import pdb
            #pdb.set_trace()
            for bucket in buckets:
                if dist_prev < bucket:
                    result[bucket]+=1
                    found = True
                    break
            if not found:
                result[int(dist_prev)] += 1
                
        for k in sorted(result.iterkeys()):
            if result[k]:
                print '%-10d %-5d' % (k,result[k])        
        
    def print_wifi_info(self):
        self.print_title('WIFI analysis')
        stations = []
        
        for report in self.reports:
            if report.is_station():
                stations.append(report)
        print 'Reports in station: %s' % len(stations)
        print 'Reports not in station: %s' % (len(self.reports) - len(stations))
            
                
                          
                          
