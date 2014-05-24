import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
try:
  import matplotlib.pyplot as plt
except ImportError:
  pass
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import gtfs.models
from ot_profiler import do_profile
import os
import config
import numpy as np
import stops
import shapes
from utils import *
from common.ot_utils import *
from common import ot_utils
import datetime
import json

GTFS_COSTOP_MATRIX_KEY = 'gtfs:costop_matrix'
GTFS_TRIP_DATA_KEY = 'gtfs:trip_data'
GTFS_TRIP_STOP_MATRIX_KEY = 'gtfs:trip_stop_matrix'
GTFS_TRIP_STOP_MATRIX_TRIP_IDS_INDS_KEY = 'gtfs:trip_stop_matrix:trip_ids_inds'

all_stops = stops.all_stops

class TripDatastore():
  def __init__(self, day):
        
    self.trip_datastore = GetTripData(day)
    self.trip_stop_matrix, self.trip_stop_matrix_trip_ids_inds = GetTripStopMatrix(day)
    self.costop_matrix = GetCostopMatrix(day)
    
  def GetImpossibleCostops(self, stop_inds):
      # we multiply AND rows so that any 0 will invalidate the stop - all stops
      # need to agree that this is a legal stop    
      # TODO(oferb): Don't need to explicitely compute possible_costops_ids if it saves time
      possible_costops_inds = (self.costop_matrix[stop_inds,:].sum(axis=0) == len(stop_inds)).astype(int)
      possible_costops_inds = possible_costops_inds.ravel().nonzero()[0]
      possible_costops_ids = [all_stops.id_list[x] for x in possible_costops_inds]
      impossible_costops_ids = [x for x in all_stops if x not in possible_costops_ids]
      impossible_costops_ind_ids = [all_stops.id_list.index(x) for x in impossible_costops_ids]
      return impossible_costops_ind_ids  
    
  def GetTripsByStops(self, stop_inds):
      trips_with_visited_stops = self.trip_stop_matrix[:,stop_inds]
      trips_with_visited_stops = (trips_with_visited_stops == 1).astype(int)
      trips_with_visited_stops = trips_with_visited_stops.sum(axis=1).nonzero()[0]
      inv_map = {v:k for k, v in self.trip_stop_matrix_trip_ids_inds.items()}
      trips_with_visited_stops = [inv_map[x] for x in trips_with_visited_stops]
      return trips_with_visited_stops    

def GenerateCostopMatrix(day, trip_data):
  costops = np.zeros((len(stops.all_stops), len(stops.all_stops)))
  for trip in trip_data:
    for stop_ind1 in trip_data[trip]['stop_inds']:
      for stop_ind2 in trip_data[trip]['stop_inds']:
        costops[stop_ind1, stop_ind2] += 1
        costops[stop_ind2, stop_ind1] += 1
  names = [stops.all_stops[x].name for x in stops.all_stops.id_list[0:-1]]
  if (0):
    import matplotlib.pyplot as plt
    plt.imshow(costops > 0, interpolation="none")
    plt.yticks(range(costops.shape[0]), names, size='small')
    locs, labels = plt.xticks(range(costops.shape[0]), names, size='small')
    plt.setp(labels, rotation=90)

  return (costops > 0).astype(int);

#@do_profile(follow=[])
def GenerateTripStopMatrix(day, trip_data, costop_matrix):
  matrix = np.zeros((len(trip_data), len(stops.all_stops)))
  trip_ids = sorted(trip_data)
  for i, trip in enumerate(trip_ids):
    trip_stop_inds = trip_data[trip]['stop_inds']
    matrix[i, trip_stop_inds] = 1
    costop_matrix[trip_stop_inds]
    possible_costops_inds = (costop_matrix[trip_stop_inds,:].sum(axis=0) == len(trip_stop_inds)).astype(int)
    impossible_costops_inds = np.arange(len(possible_costops_inds))[possible_costops_inds == 0]
    possible_costops_inds = np.arange(len(possible_costops_inds))[possible_costops_inds != 0]
    matrix[i, impossible_costops_inds] = -1
  trip_ids_inds_dict = dict(zip(trip_ids, range(len(trip_ids))))
  return matrix, trip_ids_inds_dict

#@do_profile(follow=[])
def GenerateTripData(day):
  trips = GetTripsByDay(day)
  result = {}
  for i, trip in enumerate(trips):
    result[trip.trip_id] = {}
    result[trip.trip_id]['trip_id'] = trip.trip_id
    result[trip.trip_id]['stops'] = {}
    result[trip.trip_id]['stop_inds'] = []
    stop_times = trip.get_stop_times()
    for stop_time in stop_times:
      result[trip.trip_id]['stops'][str(stop_time.stop.stop_id)] = (stop_time.stop_sequence, stop_time.arrival_time, stop_time.departure_time)
      result[trip.trip_id]['stop_inds'].append(stops.all_stops.id_list.index(stop_time.stop.stop_id))
      result[trip.trip_id]['start_time'] = stop_times[0].arrival_time
      result[trip.trip_id]['end_time'] = stop_times[-1].departure_time        
  return result
            
def GetTripsByDay(day):
  day_str = _DayToDayStr(day)
  relevant_services = gtfs.models.Service.objects.filter(start_date = day_str)
  relevant_service_ids = [x[0] for x in relevant_services.all().values_list('service_id')]
  trips = gtfs.models.Trip.objects.filter(service__in=relevant_service_ids).order_by('trip_id')
  return trips

def GetRedisData(redis_key, day=None):
  if day:
    redis_key += ':' + _DayToDayStr(day)
  data_json = load_by_key(redis_key)
  data = json.loads(data_json)
  return data

def GetCostopMatrix(day):
  costops = GetRedisData(GTFS_COSTOP_MATRIX_KEY, day)
  costops = np.array(costops)  
  return costops

def GetTripStopMatrix(day):
  trip_stop_matrix = GetRedisData(GTFS_TRIP_STOP_MATRIX_KEY, day)
  trip_ids_inds_dict = GetRedisData(GTFS_TRIP_STOP_MATRIX_TRIP_IDS_INDS_KEY, day)   
  trip_stop_matrix = np.array(trip_stop_matrix)  
  return trip_stop_matrix, trip_ids_inds_dict

def GetTripData(day):
  data_store = GetRedisData(GTFS_TRIP_DATA_KEY, day)
  for trip_key in data_store:
    stops = data_store[trip_key]['stops']
    int_stop_keys = [int(x) for x in stops.keys()]
    int_stop_dict = dict(zip(int_stop_keys, stops.values()))
    data_store[trip_key]['stops'] = int_stop_dict
  return data_store

def SetRedisData(value, redis_key, day=None):
  if day:
    redis_key += ':' + _DayToDayStr(day)
  value_json = json.dumps(value)
  save_by_key(redis_key, value_json)
  return value_json

def SetCostopMatrix(day, trip_data):
  costops = GenerateCostopMatrix(day, trip_data) 
  SetRedisData(costops.tolist(), GTFS_COSTOP_MATRIX_KEY, day)
  return costops

def SetTripData(day):
  trip_data = GenerateTripData(day) 
  SetRedisData(trip_data, GTFS_TRIP_DATA_KEY, day)
  return trip_data  
 
def SetTripStopMatrix(day, trip_data, costop_matrix):
  matrix, trip_ids_inds = GenerateTripStopMatrix(day, costop_matrix, trip_data) 
  SetRedisData(matrix.tolist(), GTFS_TRIP_STOP_MATRIX_KEY, day)
  SetRedisData(trip_ids_inds, GTFS_TRIP_STOP_MATRIX_TRIP_IDS_INDS_KEY, day)
  return matrix, trip_ids_inds

def _DayToDayStr(day):
  return day.strftime("%Y-%m-%d")

def _GTFSDayStrToDay(day):
  return datetime.datetime.strptime('010414', "%d%m%y").date()

def _AddDayToKey(key, day):
  return key + ":" + _DayToDayStr(day)

def daterange(start_date, end_date):
  for n in range(int ((end_date - start_date).days)):
    yield start_date + datetime.timedelta(n)

def ReloadRedisGTFSData():
  #days = gtfs.models.Service.objects.all().values_list('start_date', flat=True)
  #days = sorted(list(set(days)))
  days_begin_end = [_GTFSDayStrToDay('010414'), datetime.date.today()+datetime.timedelta(1)] # add 
  days = daterange(days_begin_end[0], days_begin_end[1])
  #days = days_begin_end
  days = sorted([x for x in days])
  #days = [days[0]]
  for i, day in enumerate(days):
    print i, ' of ', len(days)
    trip_data = SetTripData(day) 
    costop_matrix = SetCostopMatrix(day, trip_data)
    SetTripStopMatrix(day, costop_matrix, trip_data)

if __name__ == '__main__':
  ReloadRedisGTFSData()
  print 'done'
else:
  pass
  #trip_data = GetTripData()
  #trip_stop_matrix, trip_stop_matrix_trip_ids_inds = GetTripStopMartix()
  #costop_matrix = GetCostopMatrix()    
   
    