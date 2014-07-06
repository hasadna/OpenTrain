from django.core.management.base import BaseCommand, CommandError
import gtfs.utils
import timetable.utils
import common.ot_utils

class Command(BaseCommand):
    args = ''
    help = 'Download gtfs file from MOT'
    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('UTC Time: %s' % (common.ot_utils.get_utc_now()))
        self.stdout.write('Starting download_gtfs_file')
        dirname = gtfs.utils.download_gtfs_file()
        if not dirname:
            print 'No new gtfs info - return'
        if dirname:
            gtfs.utils.create_all(dirname=dirname,clean=True)
            timetable.utils.build_from_gtfs(2) 
            #gtfs.logic.clean_all()
        self.stdout.write('GTFS command completed')
        

                          
                          
