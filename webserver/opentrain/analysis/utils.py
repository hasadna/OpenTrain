import common.ot_utils
def find_reports_dist(r1,r2):
    my_loc1 = r1.my_loc
    my_loc2 = r2.my_loc
    result = common.ot_utils.latlon_to_meters(my_loc1.lat, my_loc1.lon, my_loc2.lat, my_loc2.lon)
    return result

def find_distance_in_reports(reports,full=False):
    reports = list(reports)
    result = []
    for idx in xrange(0,len(reports)-1):
        r1 = reports[idx]
        r2 = reports[idx+1]
        if hasattr(r1,'my_loc') and hasattr(r2,'my_loc'):
            dist = find_reports_dist(r1,r2)
            if full:
                result.append((r1,r2,dist))
            else:   
                result.append(dist)
    return result

def find_device_ids(device_pat):
    import models
    device_ids = models.Report.objects.filter(device_id__contains=device_pat).values_list('device_id',flat=True).distinct()
    return device_ids

def get_reports(device_id):
    import models
    result = list(models.Report.objects.filter(device_id=device_id).order_by('timestamp'))
    return result

def analyze_bssid(bssid):
    from models import SingleWifiReport,Report,LocationInfo
    wifi_reports = SingleWifiReport.objects.filter(key=bssid).order_by('report__timestamp')
    print 'Number of wifi reports = %d' % wifi_reports.count()
    names = SingleWifiReport.objects.filter(key=bssid).values_list('SSID',flat=True).distinct() 
    print 'Names = %s' % (','.join(names))
    reports = Report.objects.filter(id__in=wifi_reports.values_list('report')).order_by('timestamp')
    print 'Number of reports = %s' % reports.count()
    locs = list(LocationInfo.objects.filter(id__in=reports.values_list('my_loc')).order_by('timestamp'))
    print 'Number of locations = %s' % (len(locs))
    min_lat = min(loc.lat for loc in locs)
    max_lat = max(loc.lat for loc in locs)
    min_lon = min(loc.lon for loc in locs)
    max_lon = max(loc.lon for loc in locs)
    max_dist = common.ot_utils.latlon_to_meters(min_lat,min_lon,max_lat,max_lon)
    print 'Maximal distance = %.2f' % (max_dist)

    for idx,loc in enumerate(locs[0:-1]):
        loc_next = locs[idx+1]
        dist_next = locs_dist(loc,loc_next)
        time_diff = int((loc_next.timestamp - loc.timestamp).total_seconds())
        is_same_device = loc.report.device_id == loc_next.report.device_id
        if is_same_device:
            device_status = 'SAME DEVICE %s' % (loc.report.device_id)
        else:
            device_status = '%s %s' % (loc.report.device_id,loc_next.report.device_id)
        if dist_next > 100:
            print '=' * 30
            print '''%3s: Distance: %8.2f 
%s %s
%s %s Time difference: %s
%s 
''' % (idx,dist_next,loc.report.id,loc_next.report.id,loc.timestamp.replace(microsecond=0),loc_next.timestamp.replace(microsecond=0),time_diff,device_status)
            
def locs_dist(loc1,loc2):
    return common.ot_utils.latlon_to_meters(loc1.lat,loc1.lon,loc2.lat,loc2.lon)
        
