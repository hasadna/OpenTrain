from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

class Command(BaseCommand):
    help = 'Analyze bssid'
    def handle(self, *args, **options):
        import analysis.utils
        analysis.utils.analyze_bssid(args[0])



                          
                          
