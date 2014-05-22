import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'

from reports.models import RawReport
for x in xrange(int(sys.argv[1]),60000,1000):
	rrs = list(RawReport.objects.all().order_by('id')[x:x+1000]) 
        for rr in rrs:
                t = rr.get_first_item_timestamp()
                if t: 
			rr.saved_at = t
			rr.save() 
		else:
			print rr.id
        print len(rrs),x



