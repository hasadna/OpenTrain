from models import TtStop,TtStopTime,TtTrip
import gtfs.models
from timetable.models import TtShape
import json
from common import ot_utils
import datetime

def build_from_gtfs(start_date,days=30):
    build_stops()
    end_date = start_date + datetime.timedelta(days=days-1)
    print '=' * 50
    print 'Start day = %s' % (start_date)
    print 'End day = %s' % (end_date)
    clean_trips(start_date, end_date)
    build_trips(start_date, end_date)
        
def build_stops():
    stops = gtfs.models.Stop.objects.all()
    for stop in stops:
        if not TtStop.objects.filter(gtfs_stop_id=stop.stop_id).exists():
            new_stop = TtStop(gtfs_stop_id = stop.stop_id,
                              stop_name = stop.stop_name,
                              stop_lat = stop.stop_lat,
                              stop_lon = stop.stop_lon,
                              stop_url = stop.stop_url)
            new_stop.save()
            print 'Added stop %s' % (new_stop)
            
def clean_trips(from_date,to_date):
    qs = TtTrip.objects.filter(date__gte=from_date).filter(date__lte=to_date)
    print 'Going to delete %s trips of dates %s to %s (incl)' % (qs.count(),from_date,to_date)
    qs.delete()
            
def build_trips(from_date=None,to_date=None):
    trips = gtfs.models.Trip.objects.all()
    date_str = ot_utils.get_date_underscored()
    print 'Total number of trips: %s' % (trips.count())
    if from_date:
        trips = trips.filter(service__start_date__gte=from_date)
    if to_date:
        trips = trips.filter(service__end_date__lte=to_date)
    print 'number of trips in date range %s' % (trips.count())
    trips_count = trips.count()
    for idx,trip in enumerate(trips):
        print 'Building trip %s/%s' % (idx,trips_count)
        trip_date = trip.service.start_date
        new_trip = TtTrip()
        new_trip.gtfs_trip_id = trip.trip_id
        new_trip.date = trip_date
        assert trip.service.start_date == trip.service.end_date
        new_trip.shape = _get_or_build_shape(trip.shape_id, date_str)
        new_trip.save()
        _build_stoptimes(new_trip,trip)
        stops = list(new_trip.get_stop_times())
        new_trip.from_stoptime = stops[0]
        new_trip.to_stoptime = stops[-1]
        new_trip.save()
     
def _get_or_build_shape(gtfs_shape_id,date_str):
    try:
        ttshape = TtShape.objects.get(gtfs_shape_id=gtfs_shape_id,gtfs_date_str=date_str)
        return ttshape
    except TtShape.DoesNotExist:
        return _build_shape(gtfs_shape_id,date_str)
    
def _build_shape(gtfs_shape_id,date_str):
    print 'Building shape for gtfs shape id = %s date_str = %s' % (gtfs_shape_id,date_str)
    points = gtfs.models.Shape.objects.filter(shape_id=gtfs_shape_id).order_by('shape_pt_sequence')
    point_list = []
    for point in points:
        point_list.append([point.shape_pt_lat,point.shape_pt_lon])
    ttshape = TtShape(gtfs_shape_id=gtfs_shape_id,
                      gtfs_date_str=date_str,
                      points=json.dumps(point_list))
    ttshape.save()
    return ttshape
        
def _build_stoptimes(new_trip,trip):
    stoptimes = trip.stoptime_set.all().order_by('stop_sequence')
    new_stoptimes = []
    for stoptime in stoptimes:
        new_stop = TtStop.objects.get(gtfs_stop_id=stoptime.stop.stop_id)
        exp_arrival = ot_utils.db_time_to_datetime(stoptime.arrival_time,new_trip.date)
        exp_departure = ot_utils.db_time_to_datetime(stoptime.departure_time,new_trip.date)
        new_stoptime = TtStopTime(stop=new_stop,
                                  stop_sequence=stoptime.stop_sequence,
                                  trip=new_trip,
                                  exp_arrival=exp_arrival,
                                  exp_departure=exp_departure)

        new_stoptimes.append(new_stoptime)
    TtStopTime.objects.bulk_create(new_stoptimes)


