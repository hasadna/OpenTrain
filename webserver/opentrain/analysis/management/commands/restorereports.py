from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ( 
        make_option('--file',
            dest='file',
            default='/tmp/backup.gz',
            help='gz file to restore from'),)
        
    help = 'Restore reports from file'
    def handle(self, *args, **options):
        import reports.logic
        import analysis.logic
        reports.logic.restore_reports(options['file'])
        analysis.logic.analyze_raw_reports()

                          
                          
