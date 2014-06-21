from django.conf import settings
import os.path
from models import Stop,Trip

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
            
def build_trips():
    filename = os.path.join(DIR,'trips.txt')
    trip_dicts = read_csv(filename)
    new_trips = []
    for trip_dict in trip_dicts:
        t = Trip(trip_id=trip_dict['trip_id'],
                 shape_id=trip_dict['shape_id'])
                 
        new_trips.append(t)
    print 'Built %d trips, saving...' % (len(new_trips))
    Trip.objects.bulk_create(new_trips)
    print 'Trips saved # of trips in system: %d' % (Trip.objects.all().count())
            
    