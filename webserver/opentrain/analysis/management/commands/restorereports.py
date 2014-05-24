from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ( 
        make_option('--file',
            dest='file',
            default='/tmp/backup.gz',
            help='gz file to restore from'),
        make_option('--analyze_only',
            dest='analyze_only',
            action='store_true',
            default=False,
            help='donot read file, just analyze')
        )
        
    help = 'Restore reports from file'
    def handle(self, *args, **options):
        import reports.logic
        import analysis.logic
        self.stdout.write('analyze_only = %s' % (options['analyze_only']))
        self.stdout.write('file = %s' % (options['file']))
        if not options['analyze_only']:
            reports.logic.restore_reports(options['file'])
        analysis.logic.analyze_raw_reports()

                          
                          
