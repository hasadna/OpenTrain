from django.conf import settings
import os.path
from models import Stop

DIR = os.path.join(settings.BASE_DIR,'tmp_data/gtfs/zip_data/2014_06_21_18_58_46')
import csv
def read_csv(filename):
    with open(filename) as fh:
        result = []
        reader = csv.DictReader(fh, delimiter=',')
        for row in reader:
            d = dict()
            for key,value in row.iteritems():
                key_decoded = key.decode('utf-8-sig')
                value_decoded = value.decode('utf-8-sig')
                d[key_decoded] = value_decoded
            result.append(d)
        return result
                
        
def build_stops():
    filename = os.path.join(DIR,'stops.txt')
    stop_dicts = read_csv(filename)
    for stop_dict in stop_dicts:
        try:
            existing_stop = Stop.objects.get(stop_id=stop_dict['stop_id'])  # @UnusedVariable
        except Stop.DoesNotExist:
            new_stop = Stop(stop_name=stop_dict['stop_name'],
                            stop_id=stop_dict['stop_id'],
                            stop_lat=stop_dict['stop_lat'],
                            stop_lon=stop_dict['stop_lon'],
                            stop_url=stop_dict['stop_url'])
            new_stop.save()
            print 'New stop created %s' % (new_stop)
            
    