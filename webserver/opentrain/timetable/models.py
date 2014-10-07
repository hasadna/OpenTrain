from django.db import models
import common.ot_utils as ot_utils
import names
import json

class TtStop(models.Model):
    gtfs_stop_id = models.IntegerField(db_index=True,null=True)
    stop_name = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_url = models.URLField(blank=True,null=True)

    def get_short_name(self):
        return names.STOP_SHORT_NAMES.get(self.gtfs_stop_id)

    def __unicode__(self):
        return '%s %s' % (self.stop_name,self.gtfs_stop_id)
    
    def to_json(self,bssids=None):
        result =   dict(stop_name=self.stop_name,
                    latlon=[self.stop_lat,self.stop_lon],
                    gtfs_stop_id=self.gtfs_stop_id,
                    stop_short_name=self.get_short_name())
        if bssids is not None:
            result['bssids'] = bssids
        return result

class TtShape(models.Model):
    gtfs_shape_id = models.CharField(max_length=100,db_index=True)
    gtfs_date_str = models.CharField(max_length=20,default='2014_dummy')
    points = models.TextField()
    def get_points_array(self):
        return json.loads(self.points)
    
class TtTrip(models.Model):
    gtfs_trip_id = models.CharField(max_length=100,unique=True,db_index=True,null=True,blank=True)
    date = models.DateTimeField(blank=True,null=True)
    from_stoptime = models.ForeignKey('TtStopTime',null=True,related_name='first_stop')
    to_stoptime = models.ForeignKey('TtStopTime',null=True,related_name='last_stop')
    shape = models.ForeignKey(TtShape,null=True)
    
    def get_stop_times(self):
        return self.ttstoptime_set.all().order_by('stop_sequence')
    
    def get_points(self):
        import json
        return json.loads(self.shape.points)
    
    def print_stoptimes(self):
        stop_times = self.get_stop_times()
        print 'trip ' + self.gtfs_trip_id
        for stop in stop_times:
            arrival_str = ot_utils.get_localtime(stop.exp_arrival).strftime('%H:%M:%S') if ot_utils.get_localtime(stop.exp_arrival) is not None else '--:--:--'
            departure_str = ot_utils.get_localtime(stop.exp_departure).strftime('%H:%M:%S') if ot_utils.get_localtime(stop.exp_departure) is not None else '--:--:--'
            #delta_str =  delta.strftime('%M:%S') if departure is not None else '--:--'
            print '%s %s %s' % (arrival_str, departure_str, stop.stop.stop_name)

    def to_json_full(self,with_shapes=True,rt_stops=None):
        stop_times = self.get_stop_times()
        stop_times_json = []
        for st in stop_times:
            if rt_stops:
                found = [s for s in rt_stops if s.stop_id == st.stop_id]
            else:
                found = None
            stop_times_json.append(st.to_json(rt_stop=found[0] if found else None))
        result = dict(gtfs_trip_id=self.gtfs_trip_id,
                      stop_times=stop_times_json)
        if with_shapes:
            result['shapes'] = self.get_points()
        return result
    
    
    def __unicode__(self):
        stop_times = list(self.get_stop_times())
        return 'Trip %s from %s to %s' % (self.gtfs_trip_id,stop_times[0],stop_times[-1])
        
class TtStopTime(models.Model):
    trip = models.ForeignKey(TtTrip)
    stop = models.ForeignKey(TtStop)
    stop_sequence = models.IntegerField()
    exp_arrival = models.DateTimeField()
    exp_departure = models.DateTimeField()
    trip = models.ForeignKey(TtTrip)
    
    def __unicode__(self):
        return '%s at %s' % (self.stop.stop_name,self.exp_arrival)
    
    def to_json(self,rt_stop=None):
        result = dict(exp_arrival=self.exp_arrival.isoformat(),
                    exp_departure=self.exp_departure.isoformat(),
                    stop_sequence=self.stop_sequence,
                    stop=self.stop.to_json()
                    )
        if rt_stop:
            if rt_stop.act_arrival:
                result['act_arrival'] = rt_stop.act_arrival.replace(microsecond=0).isoformat()
            else:
                result['act_arrival'] = None
            if rt_stop.act_departure:
                result['act_departure'] = rt_stop.act_departure.replace(microsecond=0).isoformat()
            else:
                result['act_departure'] = None
        return result
    
