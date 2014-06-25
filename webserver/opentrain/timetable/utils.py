from django.conf import settings
import os.path
from models import TtStop,TtStopTime,TtTrip
import gtfs.models
        
def build_stops():
    stops = gtfs.models.Stop.objects.all()
    for stop in stops:
        if not TtStop.objects.filter(stop_id=stop.stop_id).exists():
            new_stop = TtStop(stop_id = stop.stop_id,
                              stop_name = stop.stop_name,
                              stop_lat = stop.stop_lat,
                              stop_lon = stop.stop_lon,
                              stop_url = stop.stop_url)
            new_stop.save()
            print 'Added stop %s' % (new_stop)
            
def build_trips():
    trips = gtfs.models.Trip.objects.all()        
    new_trips = []
    for trip in trips:
        new_trip = TtTrip()
        new_trip.trip_id = trip.trip_id
        new_trip.shape_id = trip.shape_id
        new_trip.date = trip.service.start_date
        assert trip.service.start_date == trip.service.end_date
        new_trips.append(new_trip)
    TtTrip.objects.bulk_create(new_trips)