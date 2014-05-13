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

        
