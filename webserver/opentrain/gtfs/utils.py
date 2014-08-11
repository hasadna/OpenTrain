import os
import glob

from django.conf import settings
from common import ot_utils

MOT_FTP = "gtfs.mot.gov.il"
FILE_NAME = "irw_gtfs.zip"
GTFS_DATA_DIR = os.path.join(settings.DATA_DIR,'gtfs','data')

def download_gtfs_file(force=False,gtfs_url=None):
    """ download gtfs zip file from mot, and put it in DATA_DIR in its own subfolder """
    import shutil
    time_suffix = ot_utils.get_utc_time_underscored()
    if not os.path.exists(GTFS_DATA_DIR):
        ot_utils.mkdir_p(GTFS_DATA_DIR)
    tmp_file = '/tmp/%s_tmp.zip' % (time_suffix)
    print 'downloading GTFS to tmp file'
    if not gtfs_url:     
        ot_utils.ftp_get_file(MOT_FTP,FILE_NAME,tmp_file)
    else:
        ot_utils.download_url(gtfs_url,tmp_file) 
    if not force:
        tmp_md5 = ot_utils.md5_for_file(tmp_file)
        last_dir = ot_utils.find_lastest_in_dir(GTFS_DATA_DIR)
        if last_dir:
            was_success = os.path.exists(os.path.join(last_dir,'success'))
            if not was_success:
                print 'Last time was not success'
            else:
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
    
    print 'Checksum is different or force -- copying'
    local_dir = os.path.join(GTFS_DATA_DIR,time_suffix)
    ot_utils.mkdir_p(local_dir)
    ot_utils.mkdir_p(local_dir)
    local_file = os.path.join(local_dir,FILE_NAME)
    shutil.move(tmp_file,local_file)
    ot_utils.unzip_file(local_file,local_dir)
    print 'All gtfs files are in %s' % local_dir
    return local_dir

def write_success():
    import common.ot_utils
    last_dir = ot_utils.find_lastest_in_dir(GTFS_DATA_DIR)
    with open(os.path.join(last_dir,'success'),'w') as fh:
        fh.write('success on %s\n' % common.ot_utils.get_utc_now().isoformat())

        
def find_gtfs_data_dir():
    """ returns the lastest subfolder in DATA_DIR """
    dirnames = glob.glob("%s/*" % (GTFS_DATA_DIR))
    if not dirnames:
        raise Exception("No data dir found in %s" % (GTFS_DATA_DIR))
    # return the latest
    return sorted(dirnames)[-1]


def clean_all():
    import models
    cls_list = models.GTFSModel.__subclasses__()  # @UndefinedVariable
    for cls in reversed(cls_list):
        ot_utils.delete_from_model(cls)
    
def create_all(dirname,clean=True):
    import models
    ot_utils.rmf(os.path.join(settings.BASE_DIR,'tmp_data/gtfs/processed_data'))
    cls_list = models.GTFSModel.__subclasses__()  # @UndefinedVariable
    if clean:
        clean_all()
        
    for cls in cls_list: 
        cls.read_from_csv(dirname)

    

    
