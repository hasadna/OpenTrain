import datetime
import zipfile
import os
import time

def get_utc_time_underscored():
    """ return UTC time as underscored, to timestamp folders """
    t = datetime.datetime.utcnow()
    return t.strftime('%Y_%m_%d_%H_%M_%S')

def mkdir_p(path):
    """ mkdir -p path """
    if not os.path.exists(path):
        os.makedirs(path)
    
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
    print("Unzipped %s => %s" % (fname,dir))
    
        
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

def parse_dt(dt_str):
    """ parse the datetime string as returned from the form """
    return datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M')

def normalize_time(value):
    """ we normalize time (without date) into integer based on minutes
    we ignore the seconds """
    h,m,s = [int(x) for x in value.split(':')]  # @UnusedVariable
    return h * 60 + m
    

    
    