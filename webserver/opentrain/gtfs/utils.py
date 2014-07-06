import os
import glob

from django.conf import settings
from common import ot_utils

MOT_FTP = "gtfs.mot.gov.il"
FILE_NAME = "irw_gtfs.zip"
GTFS_DATA_DIR = os.path.join(settings.DATA_DIR,'gtfs','data')

def download_gtfs_file(download_only=False):
    """ download gtfs zip file from mot, and put it in DATA_DIR in its own subfolder """
    import shutil
    time_suffix = ot_utils.get_utc_time_underscored()
    if not os.path.exists(GTFS_DATA_DIR):
        ot_utils.mkdir_p(GTFS_DATA_DIR)
    tmp_file = '/tmp/%s_tmp.zip' % (time_suffix)
    print 'downloading GTFS to tmp file'     
    ot_utils.ftp_get_file(MOT_FTP,FILE_NAME,tmp_file)
    tmp_md5 = ot_utils.md5_for_file(tmp_file)
    last_dir = ot_utils.find_lastest_in_dir(GTFS_DATA_DIR)
    if last_dir:
        last_file = os.path.join(last_dir,FILE_NAME)
        try:
            last_md5 = ot_utils.md5_for_file(last_file)
        except Exception,e:
            print e
            last_md5 = 'error_in_md5'
        if last_md5 == tmp_md5:
            print 'Checksum is identical - removing tmp file'
            os.remove(tmp_file)
            return None
    
    local_dir = os.path.join(GTFS_DATA_DIR,time_suffix)
    ot_utils.mkdir_p(local_dir)
    print 'Checksum is different- copying'
    ot_utils.mkdir_p(local_dir)
    local_file = os.path.join(local_dir,FILE_NAME)
    shutil.move(tmp_file,local_file)
    ot_utils.unzip_file(local_file,local_dir)
    print 'All gtfs files are in %s' % local_dir
    return local_dir   
        
def find_gtfs_data_dir():
    """ returns the lastest subfolder in DATA_DIR """
    dirnames = glob.glob("%s/*" % (GTFS_DATA_DIR))
    if not dirnames:
        raise Exception("No data dir found in %s" % (GTFS_DATA_DIR))
    # return the latest
    return sorted(dirnames)[-1]


    
