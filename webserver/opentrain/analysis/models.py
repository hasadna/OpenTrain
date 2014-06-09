from django.db import models 

class Report(models.Model):
    device_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
        return '%s @%s' % (self.device_id,self.timestamp)
    
    def is_station(self):
        """ this function returns using iteration and not using filter().exists()
        since it is called after prefetch_related, and using this style
        does not force acceess to the DB """
        for wifi in self.get_wifi_set_all():
            if wifi.SSID == 'S-ISRAEL-RAILWAYS':
                return True 
        return False
    
    def loc_ts_delta(self):
        if self.get_my_loc():
            return (self.timestamp - self.get_my_loc().timestamp).total_seconds()
    
    def get_timestamp_israel_time(self):
        #local_time_delta = datetime.timedelta(0,2*3600)
        #return self.timestamp + local_time_delta
        from common.ot_utils import get_localtime
        timestamp = get_localtime(self.timestamp)
        timestamp = timestamp.replace(microsecond=0)
        return timestamp
    
    def to_api_dict(self,full=False):
        result = dict()
        result['created'] = self.created.isoformat()
        result['timestamp'] = self.timestamp.isoformat()
        result['device_id'] = self.device_id
        result['id'] = self.id
        result['is_station'] = self.is_station()
        if self.my_loc:
            result['loc'] = self.my_loc.to_api_dict()
        if full:
            wifis = list(self.wifi_set.all())
            result['wifis'] = [w.to_api_dict() for w in wifis]
        return result
  
    def get_my_loc(self):
        if self.pk and hasattr(self, 'my_loc'):
            return self.my_loc
        elif not self.pk and hasattr(self, 'my_loc_mock'):
            return self.my_loc_mock
        else:
            return None

    def get_wifi_set_all(self):
        if self.pk:
            return self.wifi_set.all()
        else:
            return self.wifi_set_mock
   
class LocationInfo(models.Model):
    report = models.OneToOneField(Report,related_name='my_loc')
    accuracy = models.FloatField()
    lat = models.FloatField()
    lon = models.FloatField()
    provider = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    
    @property
    def accuracy_in_coords(self):
        from common.ot_utils import meter_distance_to_coord_distance
        return meter_distance_to_coord_distance(self.accuracy)
    
    def to_api_dict(self):
        return dict(lat=self.lat,
                    lon=self.lon,
                    id=self.id,
                    provider=self.provider,
                    accuracy=self.accuracy,
                    timestamp=self.timestamp.isoformat())
     
class SingleWifiReport(models.Model):
    report = models.ForeignKey(Report,related_name='wifi_set')
    SSID = models.CharField(max_length=50)
    frequency = models.FloatField()
    key = models.CharField(max_length=30)
    signal = models.IntegerField()
    def __unicode__(self):
        return self.SSID
    
    def to_api_dict(self):
        return dict(SSID=self.SSID,key=self.key,frequency=self.frequency,signal=self.signal)
 
class RealTimeStop(models.Model):
    tracker_id = models.CharField(max_length=40,db_index=True)
    trip = models.ForeignKey('gtfs.Trip')
    stop = models.ForeignKey('gtfs.Stop')
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField(blank=True,null=True)
    class Meta:
        unique_together = (('tracker_id','trip','stop'),)
        
    def __unicode__(self):
        import common.ot_utils
        local_at = common.ot_utils.get_localtime(self.arrival_time).time().replace(microsecond=0)
        return '%s %s @%s (exp=%s)' % (self.tracker_id,self.stop,local_at,self.get_expected())
    
    def get_expected(self):
        from gtfs.models import StopTime
        import common.ot_utils
        try:
            exp_stop_time = self.trip.stoptime_set.get(stop=self.stop)
        except StopTime.DoesNotExist:
            print 'Did not find expected - should stop here?'
            return None
        return common.ot_utils.db_time_to_datetime(exp_stop_time.arrival_time)

    