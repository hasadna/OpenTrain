from django.db import models

class TtStop(models.Model):
    stop_id = models.IntegerField(db_index=True)
    stop_name = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_url = models.URLField(blank=True,null=True)
        
    def __unicode__(self):
        return '%s %s' % (self.stop_name,self.stop_id)

class TtShape(models.Model):
    gtfs_shape_id = models.CharField(max_length=100,db_index=True)
    points = models.TextField()
    
class TtTrip(models.Model):
    trip_id = models.CharField(max_length=100,unique=True,db_index=True)
    date = models.DateTimeField(blank=True,null=True)
        
class TtStopTime(models.Model):
    trip = models.ForeignKey(TtTrip)
    stop = models.ForeignKey(TtStop)
    stop_sequence = models.IntegerField()
    exp_arrival = models.DateTimeField()
    exp_departure = models.DateTimeField()
    trip = models.ForeignKey(TtTrip)
    
