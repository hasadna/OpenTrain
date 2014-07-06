import os
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
from scipy import spatial
import os
import config
import numpy as np
import copy
from utils import *
import gtfs.services

class Shape(object):
    def __init__( self, id_, coords ) :
        self.id = id_
        self.coords = coords

class ShapeList(dict):
    def __init__(self, gtfs_shapes_data) :
        #self.point_shape_ids = []
        self.all_unique_coords = []
        #for gtfs_shape in gtfs_shapes_data:
            #self.point_shape_ids.append(shape_point[0])
            #all_coords.append([float(shape_point[1]), float(shape_point[2])])
            
        ##self.point_shape_ids = [x[0] for x in list(django_shape_coords_and_ids.all().values_list('shape_id'))]
        #self.point_shape_ids = np.array(self.point_shape_ids)
        ##lat_list = [float(x[0]) for x in list(django_shape_coords_and_ids.all().values_list('shape_pt_lat'))]
        ##lon_list = [float(x[0]) for x in list(django_shape_coords_and_ids.all().values_list('shape_pt_lon'))]      
        ##all_coords = zip(lat_list, lon_list)
        #all_coords = np.array(all_coords)
        
        #unique_shape_ids = list(set(self.point_shape_ids))
        #unique_shape_ids.sort()
        #self.point_shape_int_ids = [unique_shape_ids.index(x) for x in self.point_shape_ids]
        #self.point_shape_int_ids = np.array(self.point_shape_int_ids)
        self.id_list = []
        
        import json
        for gtfs_shape in gtfs_shapes_data:
            shape_coords = json.loads(gtfs_shape.points)
            shape = Shape(gtfs_shape.shape_id, shape_coords)
            self[shape.id] = shape
            self.id_list.append(shape.id)
            self.all_unique_coords.extend(shape_coords)
        
        self.sampled_point_inds, self.sampled_point_tree = self.get_sampling_of_all_routes()

    def __getstate__(self):
        ret = self.__dict__.copy()
        ret['all_coords'] = self.point_tree.data
        ret['sampled_coords'] = self.sampled_point_tree.data
        del ret['point_tree']
        del ret['sampled_point_tree']
        return ret

    def __setstate__(self, dict):
        self.point_tree = spatial.cKDTree(dict['all_coords'])
        self.sampled_point_tree = spatial.cKDTree(dict['sampled_coords'])
        del dict['all_coords']
        del dict['sampled_coords']
        self.__dict__.update(dict)           
    
    #def query_all_points(self, coords, accuracies)   :
        
        #res_shape_point_ids = query_coords(self.point_tree, coords, accuracies)    
        
        #if (len(res_shape_point_ids) > 0):
            #if isinstance(res_shape_point_ids[0], (list, tuple)):
                #res_shape_int_ids = copy.deepcopy(res_shape_point_ids)
                #for i in xrange(len(res_shape_int_ids)):
                    #res_shape_int_ids[i] = self.point_shape_int_ids[res_shape_int_ids[i]]
            #else:
                #res_shape_int_ids = self.point_shape_int_ids[res_shape_point_ids]
        #else:
            #res_shape_int_ids = []
            
        #res_shape_ids = [self.id_list[i] for i in res_shape_int_ids]

        #return res_shape_point_ids, res_shape_ids

    def query_sampled_points(self, coords, accuracies)   :
        sampled_coord_ids = query_coords(self.sampled_point_tree, coords, accuracies)
        if sampled_coord_ids and type(sampled_coord_ids[0]) == list:
            sampled_coord_ids = [x[0] for x in sampled_coord_ids]
        sampled_coord_coords = self.sampled_point_tree.data[sampled_coord_ids]
        return sampled_coord_ids, sampled_coord_coords

    
    def get_sampling_of_all_routes(self):
        from common.ot_utils import meter_distance_to_coord_distance
        shape_point_tree = spatial.cKDTree(self.all_unique_coords)
        
        inds_to_go_over = np.zeros(len(self.all_unique_coords)) == 0
        inds_to_keep = np.zeros(len(self.all_unique_coords)) == -1
        dist_threshold = meter_distance_to_coord_distance(config.route_sampling__min_distance_between_points_meters)
        count = 0
        while count < len(inds_to_go_over):
            while(count < len(inds_to_go_over) and not inds_to_go_over[count]):
                count = count + 1
            if count < len(inds_to_go_over):
                inds_to_keep[count] = True
                inds_to_remove = shape_point_tree.query_ball_point(shape_point_tree.data[count], dist_threshold)
                inds_to_go_over[inds_to_remove] = False
            
            
        sampled_all_routes_tree = spatial.cKDTree(shape_point_tree.data[inds_to_keep])
        return inds_to_keep, sampled_all_routes_tree
  

all_shapes = ShapeList(list(gtfs.services.get_all_shapes()))
