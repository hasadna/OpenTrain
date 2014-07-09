import datetime
import zipfile
import os
import time
from django.conf import settings
from django.utils import timezone
import pytz

def datetime_to_db_time(adatetime):
    if adatetime.hour < 3: # if it's a night train, add 24 hours:
        added_time = 24 * 3600
    else:
        added_time = 0
    return adatetime.hour * 3600 + 60 * adatetime.minute + adatetime.second + added_time

def datetime_range_to_db_time(datetime1, datetime2):
    d1 = datetime_to_db_time(datetime1)
    d2 = datetime_to_db_time(datetime2)
    if d1 > d2: # in gtfs, instead of midnight passing to the next day, you count in more time for the same day, i.e 25:00 instead of 01:00
        d2 = d2 + 24*3600    
    return d1,d2

def db_time_to_datetime(db_time, date=None):
    result = datetime.time(db_time / 3600 % 24, (db_time % 3600) / 60, db_time % 60)
    if date:
        result = datetime.datetime.combine(date, result)
    return get_localtime(result)

def get_utc_time_underscored():
    """ return UTC time as underscored, to timestamp folders """
    t = datetime.datetime.utcnow()
    return t.strftime('%Y_%m_%d_%H_%M_%S')

def get_days_after_today(days):
    t = datetime.date.today()
    timedelta = datetime.timedelta(days=days)
    return t + timedelta


def get_local_time_underscored():
    """ return time as underscored, to timestamp folders """
    t = datetime.datetime.now()
    return t.strftime('%Y_%m_%d_%H_%M_%S')

def mkdir_p(path):
    """ mkdir -p path """
    if not os.path.exists(path):
        os.makedirs(path)
    
def rmf(path):
    import shutil
    print 'Trying to delete path %s' % (path)
    if os.path.exists(path):
        print 'Deleting path %s' %(path)
        shutil.rmtree(path)
    
def download_url(url,local_path):
    import requests
    resp = requests.get(url)
    with open(local_path,'w') as fh:
        fh.write(resp.content)
    print 'Copied %s to %s' % (url,local_path)
    
    
def ftp_get_file(host,remote_name,local_path):
    """ get file remote_name from FTP host host and copied it inot local_path"""
    from ftplib import FTP
    f = FTP(host)
    f.login()
    fh = open(local_path,'wb')
    f.retrbinary('RETR %s' % (remote_name), fh.write)
    fh.close()
    f.quit()
    print("Copied from host %s: %s => %s" % (host,remote_name,local_path))
    
    
def unzip_file(fname,dirname):
    """ unzip file fname into dirname """
    zf = zipfile.ZipFile(fname)
    zf.extractall(path=dirname)
    print("Unzipped %s => %s" % (fname,dirname))
    
        
def benchit(func):
    """ decorator to measure time """
    def wrap(*args,**kwargs):
        time_start = time.time()
        res = func(*args,**kwargs)
        time_end = time.time()
        delta = time_end - time_start
        print('Function %s took %.2f seconds' % (func.__name__,delta))
        return res
    return wrap

def benchit_and_db(func):
    def wrap(*args,**kwargs):
        from django.db import connection
        q1 = len(connection.queries)
        time_start = time.time()
        res = func(*args,**kwargs)
        time_end = time.time()
        delta = time_end - time_start
        q2 = len(connection.queries)
        print('Function %s took %.2f seconds %s DB calls' % (func.__name__,delta,q2-q1))
        for idx in xrange(q1,q2):
            print connection.queries[idx]
        return res
    return wrap



def parse_form_date(dt_str):
    """ parse the datetime string as returned from the form """
    import dateutil.parser
    if not dt_str or dt_str.lower() == 'none':
        return None
    return dateutil.parser.parse(dt_str)


def parse_gtfs_date(value):
    year = int(value[0:4])
    month = int(value[4:6])
    day = int(value[6:8])
    return datetime.date(year,month,day)

def parse_bool(value):
    int_value = int(value)
    return True if int_value else False 

def normalize_time(value):
    """ we normalize time (without date) into integer based on minutes
    we ignore the seconds """
    h,m,s = [int(x) for x in value.split(':')]  # @UnusedVariable
    return h * 60*60 + m * 60 + s
    
def denormalize_time_to_string(value):
    s = value % 60
    value = value - s
    value = value / 60
    m = value % 60
    h = value / 60
    return '%02d:%02d:%02d' % (h,m,s)
    
def get_weekdayname(dt):
    return dt.strftime('%A')
    
def get_utc_time_from_timestamp(ts):
    return datetime.datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
    
def get_utc_now():
    return datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
    
def get_localtime_now():
    return get_localtime(get_utc_now())
    
def delete_from_model(*models):
    from django.db import connection
    cursor = connection.cursor()
    table_names = [model._meta.db_table for model in models]
    sql = "truncate %s RESTART IDENTITY CASCADE;" % (','.join(table_names))
    cursor.execute(sql)    
    print 'DELETED %s' % (table_names)

def get_localtime(dt):
    tz = pytz.timezone(settings.TIME_ZONE)
    if dt.tzinfo:
        return dt.astimezone(tz)
    else:
        return tz.localize(dt)

def get_normal_time(dt):
    local_dt = get_localtime(dt)
    h = local_dt.hour
    m = local_dt.minute
    s = local_dt.second
    return h*3600+60*m+s

def dt_time_to_unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    delta = dt - epoch
    return delta.total_seconds()

def unix_time_to_localtime(ts):
    dt = datetime.datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.UTC)
    return get_localtime(dt)

def meter_distance_to_coord_distance(meter_distance):
    """ the following (non-exact) calculation yields a conversion from meter distances 
        to lat-lon distance which should be accurate enough for Israel
        tel_aviv = [32.071589, 34.778227]
        rehovot = [31.896010, 34.811525]
        meter_distance = 19676
        delta_coords = [tel_aviv[0]-rehovot[0], tel_aviv[1]-rehovot[1]]
        delta_coords_norm = (delta_coords[0]**2 + delta_coords[1]**2)**0.5
        meters_over_coords = meter_distance/delta_coords_norm # equals 110101 """
    meters_over_coords = 110101.0
    return meter_distance/meters_over_coords

def latlon_to_meters(lat1,lon1,lat2,lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    from math import radians, cos, sin, asin, sqrt
    # convert decimal degrees to radians 
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km * 1000

def autoregister(*app_list):
    from django.db.models import get_models, get_app
    from django.contrib import admin
    from django.contrib.admin.sites import AlreadyRegistered
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass

def md5_for_file(path, block_size=32768):
    '''
    Block size directly depends on the block size of your filesystem
    to avoid performances issues
    Here I have blocks of 4096 octets (Default NTFS)
    '''
    import hashlib
    md5 = hashlib.md5()
    with open(path,'rb') as f: 
        for chunk in iter(lambda: f.read(block_size), b''): 
            md5.update(chunk)
    return md5.hexdigest()

def find_lastest_in_dir(dirname):
    def ctime_in_dirname(f):
        return os.path.getctime(os.path.join(dirname,f))
    if os.path.exists(dirname):
        files = os.listdir(dirname)
        if files:
            newest = max(os.listdir(dirname), key = ctime_in_dirname)
            return os.path.join(dirname,newest)
    return None
    
    
def json_dump_dt(obj):
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial

def json_hook_dt(obj):
    import dateutil.parser
    if 'exp_arrival' in obj:
        obj['exp_arrival'] = dateutil.parser.parse(obj['exp_arrival'])
    if 'exp_departure' in obj:
        obj['exp_departure'] = dateutil.parser.parse(obj['exp_departure'])
    return obj
        