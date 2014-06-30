import models
import json

def get_trip(trip_id):
    return models.Trip.objects.get(trip_id=trip_id)

def get_trips_by_day(day):
    #day_str = _DayToDayStr(day) # remove this line if non-string day works
    relevant_services = models.Service.objects.filter(start_date = day)
    relevant_service_ids = [x[0] for x in relevant_services.all().values_list('service_id')]
    # eran: do prefetch related
    trips = models.Trip.objects.filter(service__in=relevant_service_ids).order_by('trip_id').prefetch_related('stoptime_set','stoptime_set__stop')
    return trips
    
def get_all_days():
    days = models.Service.objects.all().values_list('start_date', flat=True).distinct()
    return days

def get_shape():
    models.Shape.objects.filter(shape_id=trip.shape_id).order_by('shape_pt_sequence')
    
def get_shape_coords_by_trip(trip):
    shape_id = trip.shape_id
    shape_json = models.ShapeJson.objects.get(shape_id=shape_id)
    return json.loads(shape_json.points)
    
def get_trip_stop_times(trip):
    return models.StopTime.objects.filter(trip=trip).order_by('arrival_time')

def get_all_shapes():
    all_shapes = list(models.ShapeJson.objects.all())
    return all_shapes

def get_all_stops_ordered_by_id():
    return models.Stop.objects.all().order_by('stop_id')

def print_trip_stop_times(trip_id):
    trip = get_trip(trip_id)
    print('')
    trip.print_stoptimes()
    print('')