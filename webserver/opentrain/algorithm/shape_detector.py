import gtfs.models
from scipy import spatial
import os
import config
import numpy as np
import copy
import stops
import shapes
from sklearn.hmm import MultinomialHMM
from utils import *
from common.ot_utils import *
from collections import deque
from common import ot_utils
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
import datetime
import bssid_tracker 
from redis_intf.client import (get_redis_pipeline, 
                               get_redis_client,
                               load_by_key, 
                               save_by_key)
import json
from utils import enum
from redis import WatchError

def get_train_tracker_counters_key(tracker_id):
    return "train_tracker:%s:counters" % (tracker_id)

def get_train_tracker_total_key(tracker_id):
    return "train_tracker:%s:total" % (tracker_id)

def get_shape_probs(tracker_id):
    p.zrange(get_train_tracker_counters_key(tracker_id), 0, -1, withscores=True)
    p.get(get_train_tracker_total_key(tracker_id))
    res = p.execute()
    
    # need to take shape_counts, shape_counts from res
    return shape_counts/float(max(shape_counts))

def get_shape_ids_with_high_probability(tracker_id):
    shape_int_ids = np.where(get_shape_probs(tracker_id) >= config.shape_probability_threshold)[0]
    shape_ids = [shapes.all_shapes[x].id for x in shape_int_ids]
    return shape_ids

def add_report(tracker_id, report):
    pass

