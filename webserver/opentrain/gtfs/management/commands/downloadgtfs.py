from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import gtfs.utils

class Command(BaseCommand):
    args = ''
    help = 'Download gtfs file from MOT'
    option_list = BaseCommand.option_list + (
            make_option('--todb',
            action='store_true',
            dest='todb',
            default=False,
            help='Store also to db'),
        )
    def handle(self, *args, **options):
        download_only = not options['todb']
        self.stdout.write('Starting download_gtfs_file(donwload_only=%s)' % (download_only))
        gtfs.utils.download_gtfs_file(download_only=download_only)
        self.stdout.write('GTFS command completed')
        

                          
                          
