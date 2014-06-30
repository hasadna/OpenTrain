import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
from scipy import spatial
import os
import config
import numpy as np
import copy
import config
import gtfs.services

from utils import *

NOSTOP_ID = -1

class Stop(object):
    def __init__( self, id_, name, coords ) :
        self.id = id_
        self.name = name
        self.coords = coords
        
    def __str__(self):
        return str(self.id) + ' ' + self.name

class StopList(dict):

    def __init__(self) :
        super(StopList, self).__init__()
        
        stops = gtfs.services.get_all_stops_ordered_by_id()
        stops = list(stops)
        
        self.id_list = []
        stop_coords = []
        for i, gtfs_stop in enumerate(stops):
            coord = (gtfs_stop.stop_lat, gtfs_stop.stop_lon)
            stop = Stop(gtfs_stop.stop_id, gtfs_stop.stop_name, coord)
            stop_coords.append(coord)
            self.id_list.append(stop.id)
            self[stop.id] = stop
        
        coord = (None, None)
        stop = Stop(NOSTOP_ID, 'nostop', coord)
        self[stop.id] = stop
        self.id_list.append(NOSTOP_ID)
        stop_coords = np.array(stop_coords)
        self.point_tree = spatial.cKDTree(stop_coords)               

    def __getstate__(self):
        ret = self.__dict__.copy()
        ret['stop_coords'] = self.point_tree.data
        del ret['point_tree']
        return ret

    def __setstate__(self, dict):
        self.point_tree = spatial.cKDTree(dict['stop_coords'])
        del dict['stop_coords']
        self.__dict__.update(dict)           
    
    def query_stops(self, coords, accuracies)   :
        
        res_coord_int_ids = query_coords(self.point_tree, coords, accuracies)   
        if len(res_coord_int_ids) == 1:
            res_coord_int_ids = [res_coord_int_ids]
        res_coord_ids = [self.id_list[i[0]] if i else NOSTOP_ID for i in res_coord_int_ids]
        return res_coord_ids


def get_all_stops():
    all_stops = StopList()    
    return all_stops

all_stops = get_all_stops()
