import os
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'
import analysis.models
import numpy as np
from scipy import spatial
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import simplekml
import config
import itertools
import datetime

def enum(**enums):
    return type('Enum', (), enums)

def get_XY_pos(relativeNullPoint, p):
    """ Calculates X and Y distances in meters.
    """
    deltaLatitude = p.latitude - relativeNullPoint.latitude
    deltaLongitude = p.longitude - relativeNullPoint.longitude
    latitudeCircumference = 40075160 * cos(relativeNullPoint.latitude * pi / 180)
    resultX = deltaLongitude * latitudeCircumference / 360
    resultY = deltaLatitude * 40008000 / 360
    return resultX, resultY

def query_coords(point_tree, query_coords, query_accuracies):
    if isinstance( query_accuracies, ( int, long, float ) ):
        res = list(point_tree.query_ball_point(query_coords, query_accuracies))
    else:
        res = [point_tree.query_ball_point(query_coords[i], query_accuracies[i]) for i in xrange(len(query_accuracies))]
    return res


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def is_strictly_increasing(L):
    return all(x<y for x, y in zip(L, L[1:])) 

def is_increasing(L):
    return all(x<=y for x, y in zip(L, L[1:])) 

def find_index_of_first_consecutive_value(values, start_index):
    res = None
    for i in reversed(range(start_index)):
        if values[i] != values[start_index]:
            res = i+1
            break
        elif i == 0:
            res = 0
            break        
    
    return res

def get_report_counts_and_dates(do_print=False):
    result = []
    device_ids = analysis.models.Report.objects.values_list('device_id', flat=True).distinct()
    for device_id in device_ids:
        count = analysis.models.Report.objects.filter(device_id=device_id).count()
        report = analysis.models.Report.objects.filter(device_id=device_id).order_by('timestamp')[:1].get()
        result.append((report.timestamp.date(), count, device_id))
    result = sorted(result)
    if do_print:
        for x in result:
            print x    
    return result        
    
        

if __name__ == '__main__':
    pass
    get_report_counts_and_dates(True)
