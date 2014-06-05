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
    wifi_reports = SingleWifiReport.objects.filter(key=bssid)
    print 'Number of wifi reports = %d' % wifi_reports.count()
    reports = Report.objects.filter(id__in=wifi_reports.values_list('report'))
    print 'Number of reports = %s' % reports.count()
    locs = LocationInfo.objects.filter(id__in=reports.values_list('my_loc'))
    print 'Number of locations = %s' % (locs.count())
    min_lat = min(locs.values_list('lat',flat=True))
    max_lat = max(locs.values_list('lat',flat=True))
    min_lon = min(locs.values_list('lon',flat=True))
    max_lon = max(locs.values_list('lon',flat=True))
    max_dist = common.ot_utils.latlon_to_meters(min_lat,min_lon,max_lat,max_lon)
    print 'Maximal distance = %.2f' % (max_dist)
