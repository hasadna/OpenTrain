import redis
import json

_CLIENT = redis.StrictRedis()

def get_redis_client():
    return _CLIENT

def get_redis_pipeline():
    return _CLIENT.pipeline()

def load_by_key(key, default=None, cl=None, logger=None):
    if not cl:
        cl = _CLIENT    
    val = cl.get(key)
    if logger:
        logger.info('key={} val={}'.format(key, val))
    if val:
        return json.loads(val)
    return default

def save_by_key(key, value, timeout=None, cl=None):
    if not cl:
        cl = _CLIENT
    if timeout:
        cl.setex(key, timeout, json.dumps(value))
    else:
        cl.set(key, json.dumps(value))