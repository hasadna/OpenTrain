from django.db import models

class TtStop(models.Model):
    gtfs_stop_id = models.IntegerField(db_index=True,null=True)
    stop_name = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_url = models.URLField(blank=True,null=True)
        
    def __unicode__(self):
        return '%s %s' % (self.stop_name,self.gtfs_stop_id)

class TtShape(models.Model):
    gtfs_shape_id = models.CharField(max_length=100,db_index=True,unique=True)
    points = models.TextField()
    
class TtTrip(models.Model):
    gtfs_trip_id = models.CharField(max_length=100,unique=True,db_index=True,null=True,blank=True)
    date = models.DateTimeField(blank=True,null=True)
    def __unicode__(self):
        stop_times = list(self.stoptime_set.all().order_by('stop_sequence'))
        return 'Trip %s from %s to %s' % (self.gtfs_trip_id,stop_times[0],stop_times[-1])
        
class TtStopTime(models.Model):
    trip = models.ForeignKey(TtTrip)
    stop = models.ForeignKey(TtStop)
    stop_sequence = models.IntegerField()
    exp_arrival = models.DateTimeField()
    exp_departure = models.DateTimeField()
    trip = models.ForeignKey(TtTrip)
    
    def __unicode__(self):
        return 'arrive to %s at %s' % (self.exp_arrival,self.stop.stop_name)
 