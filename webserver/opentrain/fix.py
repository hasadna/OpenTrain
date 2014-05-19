for x in xrange(0,60000,1000):
	rrs = list(RawReport.objects.all().order_by('id')[x:x+1000]) 
        for rr in rrs:
                t = rr.get_first_item_timestamp()
                if t: rr.save() 
        print len(rrs),x



