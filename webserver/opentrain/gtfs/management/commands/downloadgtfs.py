from django.core.management.base import BaseCommand, CommandError
import gtfs.utils
import timetable.utils
import common.ot_utils
import datetime
from optparse import make_option

class Command(BaseCommand):
    args = ''
    help = 'Download gtfs file from MOT'
    option_list = BaseCommand.option_list + (
        make_option('--from',
            dest='from',
            help='date to start from format: d/m/year, default is tomorrow'),
        make_option('--days',
            dest='days',
            default=30,
            type=int,
            help='number of days'),
        make_option('--forcegtfs',
                     dest='forcegtfs',
                     action='store_true',
                     default=False,
                     help='ignore checksum check and force download gtfs'),
        make_option('--gtfs',
                     dest='gtfs',
                     help='gtfs url'),
        )
    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        assert options['days'] > 0,'Days must be positive but got %s' % (options['days'])
        start_date_str = options['from']
        if start_date_str:
            (d,m,y) = start_date_str.split('/')
            d = int(d)
            m = int(m)
            y = int(y)
            assert y >= 2000,'Illegal year in date %s' % (start_date_str)
            assert 1 <= d <= 31,'Illegal day in date %s' % (start_date_str)
            assert 1 <= m <= 12,'Illegal month in date %s' % (start_date_str)
            start_date = datetime.date(year=y,month=m,day=d)
        else:
            start_date = common.ot_utils.get_days_after_today(1)
        self.stdout.write('UTC Time: %s' % (common.ot_utils.get_utc_now()))
        self.stdout.write('Start date: %s' % (start_date))
        self.stdout.write('Starting download_gtfs_file')
        dirname = gtfs.utils.download_gtfs_file(force=options['forcegtfs'],gtfs_url=options['gtfs'])
        if not dirname:
            print 'No new gtfs info'
        if dirname:
            print 'Building timetable info from = %s number of days = %s' % (start_date,
                                                                           options['days'])
            gtfs.utils.create_all(dirname=dirname, clean=True)
            timetable.utils.build_from_gtfs(start_date, options['days']) 
            gtfs.utils.clean_all()
        gtfs.utils.write_success()
        self.stdout.write('GTFS command completed')
        

                          
                          
