from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import analysis.utils

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ( 
         make_option('--days',
            type=int,
            dest='days',
            default=-1,
            help='days back to store'),
        make_option('--file',
            dest='file',
            default='/tmp/backup.gz',
            help='gz file to back to'),)
        
    help = 'Backup reports to file'
    def handle(self, *args, **options):
        import reports.logic
        reports.logic.backup_reports(options['file'],options['days'])

                          
                          
