from django.core.management.base import BaseCommand, CommandError
import gtfs.utils
import timetable.utils
import common.ot_utils
from optparse import make_option

class Command(BaseCommand):
    args = ''
    help = 'Download gtfs file from MOT'
    option_list = BaseCommand.option_list + (
        make_option('--from',
            dest='from_days',
            default=1,
            type=int,
            help='days after today to start from'),
        make_option('--to',
            dest='to_days',
            default=31,
            type=int,
            help='days after today to end in'),
        make_option('--forcegtfs',
                     dest='forcegtfs',
                     action='store_true',
                     default=False,
                     help='ignore checksum check and force download gtfs')                        
        )
    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('UTC Time: %s' % (common.ot_utils.get_utc_now()))
        self.stdout.write('Starting download_gtfs_file')
        dirname = gtfs.utils.download_gtfs_file(force=options['forcegtfs'])
        if not dirname:
            print 'No new gtfs info'
        if dirname:
            print 'Building timetable info from_days = %s to_days = %s' % (options['from_days'],
                                                                           options['to_days'])
            gtfs.utils.create_all(dirname=dirname,clean=True)
            timetable.utils.build_from_gtfs(options['from_days'],options['to_days']) 
            #gtfs.logic.clean_all()
        self.stdout.write('GTFS command completed')
        

                          
                          
