from django.conf import settings
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
            
def build_trips(from_date=None):
    trips = gtfs.models.Trip.objects.all()        
    for trip in trips:
        trip_date = trip.service.start_date
        if from_date and trip_date < from_date:
            continue
        new_trip = TtTrip()
        new_trip.trip_id = trip.trip_id
        new_trip.shape_id = trip.shape_id
        new_trip.date = trip_date
        assert trip.service.start_date == trip.service.end_date
        new_trip.save()
        build_stoptimes(new_trip)
        
def build_stoptimes(new_trip,trip):
    import common.ot_utils
    stoptimes = trip.stoptime_set.all().order_by('stop_sequence')
    new_stoptimes = []
    for stoptime in stoptimes:
        new_stop = TtStop.objects.get(stop_id=stoptime.stop.id)
        exp_arrival = common.ot_utils.db_time_to_datetime(stoptime.arrival_time,new_trip.date)
        exp_departure = common.ot_utils.db_time_to_datetime(stoptime.departure_time,new_trip.date)
        new_stoptime = TtStopTime(stop=new_stop,
                                  stop_sequence=stoptime.stop_sequence,
                                  trip=new_trip,
                                  exp_arrival=exp_arrival,
                                  exp_departure=exp_departure)

        new_stoptimes.append(new_stoptime)
        TtStopTime.objects.bulk_create(new_stoptimes)

    