import models
import common.ot_utils
import json
import gzip

def restore_reports(filename,clean=True):
    """ restore reports from main server and restore them in
    local server - cleans first """
    if not filename.endswith('gz'):
        raise Exception('%s must be gz file' % (filename))
    if clean:
        print 'Deleting current raw reports'
        common.ot_utils.delete_from_model(models.RawReport)
    rrs = []
    with gzip.open(filename,'r') as fh:
        for line in fh:
            item = json.loads(line)
            rr = models.RawReport(text=item['text'])
            rrs.append(rr)
            if len(rrs) >= 1000:
                print 'Read %d raw reports from %s- saving to DB' % (len(rrs),filename)
                models.RawReport.objects.bulk_create(rrs)
                print 'Saved to DB. # of items in DB = %s' % (models.RawReport.objects.count())
                rrs = []
        print 'Read %d raw reports from %s- saving to DB' % (len(rrs),filename)
        models.RawReport.objects.bulk_create(rrs)
        print 'Saved to DB. # of items in DB = %s' % (models.RawReport.objects.count())
        rrs = []
            

    
def backup_reports(filename,days):
    import datetime
    chunk = 30
    index = 0
    from_ts = None
    if days > 0:
        from_ts = common.ot_utils.get_utc_now() - datetime.timedelta(days=days)
    
    if not filename.endswith('.gz'):
        raise Exception('filename must be gz file')
    
    with gzip.open(filename,'w') as fh:
        if from_ts:
            all_reports = models.RawReport.objects.filter(saved_at__gt=from_ts)
        else:
            all_reports = models.RawReport.objects.all()
        all_reports = all_reports.order_by('id')
        total_count = all_reports.count() 
        while True:
            reports = all_reports[index:index+chunk]
            reports_len = reports.count()
            if reports_len == 0:
                break
            for rr in reports:
                fh.write(json.dumps(rr.to_json()))
                fh.write("\n")
            index += reports_len
            print 'so far %s / %s' % (index,total_count)
    print 'Backup %s reports to %s' % (index,filename)
            

def copy_device_reports(device_id,filename):
    chunk = 100
    index = 0
    wrote_count = 0
    
    with open(filename,'w') as fh:
        while True:
            reports = models.RawReport.objects.filter().order_by('id')[index:index+chunk]
            reports_len = reports.count()
            if reports_len == 0:
                break
            for rr in reports:
                rr_body = json.loads(rr.text)
                if rr_body['items'][0]['device_id'] == device_id:
                    fh.write(rr.text)
                    fh.write('\n')
                    wrote_count += len(rr_body['items'])
            index += reports_len
    print 'Wrote %s reports of device_id %s to %s' % (wrote_count,device_id,filename)
    
        
        
    
    
    
    
    
    
