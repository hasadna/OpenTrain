from django.db import models
import csv
import os

import common.ot_utils

class GTFSModel(models.Model):
    class Meta:
        abstract = True
    
    @classmethod
    def read_from_csv(cls,dirname):
        full = os.path.join(dirname,cls.filename)
        print('Reading from %s from class %s' % (full,cls.__name__))
        with open(full) as fh:
            reader = csv.DictReader(fh, delimiter=',')
            index = 0
            objs_to_save = []
            fields_dict = dict()
            for f in cls._meta.fields:
                fields_dict[f.name] = f
                
            for row in reader:
                index+=1
                m = cls()
                
                for (key,value) in row.iteritems():
                    key_decoded = key.decode('utf-8-sig')
                    value_decoded = value.decode('utf-8-sig')
                    is_field = False
                    if key_decoded in fields_dict:
                        is_field = True
                        field_name = key_decoded
                    if not is_field and key_decoded.endswith('_id') and key_decoded[:-3] in fields_dict:
                        is_field = True
                        field_name = key_decoded[:-3]
                    if not is_field:
                        raise Exception('key %s is not a field of %s' % (key,cls.__name__))
                    field = fields_dict[field_name]
                    # check if method set_<key> was defined
                    setter = getattr(m,'set_%s' % (field_name),None)
                    if setter:
                        setter(value_decoded)
                    else:
                        if isinstance(field,models.BooleanField):
                            setattr(m,field_name,common.ot_utils.parse_bool(value))
                        else:
                            setattr(m,key_decoded,value_decoded)
                objs_to_save.append(m)
                if index % 50000 == 0:
                    cls.objects.bulk_create(objs_to_save)
                    print('%s: Saved %d rows so far' % (cls.__name__,index))
                    objs_to_save = []
            cls.objects.bulk_create(objs_to_save)
            print('%s: Saved %d rows so far' % (cls.__name__,index))
            objs_to_save = []
        
                    
class Agency(GTFSModel):
    filename = "agency.txt"
    agency_id = models.IntegerField(primary_key=True,default=1,max_length=255)
    agency_name = models.TextField()
    agency_url = models.TextField()
    agency_timezone = models.TextField()
    agency_lang = models.CharField(max_length=20)
    def __unicode__(self):
        return self.agency_name
      
class Route(GTFSModel):
    filename = "routes.txt"
    route_id = models.IntegerField(primary_key=True)
    agency = models.ForeignKey('Agency',null=True,blank=True)
    route_short_name = models.CharField(max_length=255)
    route_long_name = models.CharField(max_length=255)
    route_desc = models.TextField()
    route_type = models.IntegerField()
    route_color = models.CharField(max_length=10)
    route_text_color = models.CharField(max_length=20)
    def __unicode__(self):
        return '%s : %s' % (self.route_id,self.route_long_name)


class Service(GTFSModel):
    filename = "calendar.txt"
    service_id = models.CharField(max_length=100,primary_key=True)
    monday = models.BooleanField()
    tuesday = models.BooleanField()
    wednesday = models.BooleanField()
    thursday = models.BooleanField()
    friday = models.BooleanField()
    saturday = models.BooleanField()
    sunday = models.BooleanField()
    start_date = models.DateField()
    end_date = models.DateField()
        
    def set_start_date(self,value):
        self.start_date = common.ot_utils.parse_gtfs_date(value)
        
    def set_end_date(self,value):
        self.end_date = common.ot_utils.parse_gtfs_date(value)
        
    
    def __unicode__(self):
        return self.service_id

    
class Trip(GTFSModel):
    filename = "trips.txt"
    route = models.ForeignKey('Route')
    service = models.ForeignKey('Service')
    trip_id = models.CharField(max_length=100,primary_key=True)
    direction_id = models.IntegerField()
    shape_id = models.CharField(max_length=100)
    wheelchair_accessible = models.IntegerField()
    trip_headsign = models.CharField(max_length=100)
    #total_start_time = models.IntegerField()
    #total_end_time = models.IntegerField()
        
    def __unicode__(self):
        return self.trip_id
            
class Stop(GTFSModel):
    filename = "stops.txt"
    stop_id = models.IntegerField(primary_key=True)
    stop_name = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_url = models.URLField()
    location_type = models.IntegerField()
    
    def __unicode__(self):
        return self.stop_name

class StopTime(GTFSModel):
    filename = "stop_times.txt"
    trip = models.ForeignKey('Trip')
    arrival_time = models.IntegerField()
    departure_time = models.IntegerField()
    stop = models.ForeignKey('Stop')
    stop_sequence = models.IntegerField() 
    def set_arrival_time(self,value):
        self.arrival_time = common.ot_utils.normalize_time(value)
        
    def json_arrival_time(self):
        return common.ot_utils.denormalize_time_to_string(self.arrival_time) 
        
    def set_departure_time(self,value):
        self.departure_time = common.ot_utils.normalize_time(value)
    
    def json_departure_time(self):
        return common.ot_utils.denormalize_time_to_string(self.departure_time)
        
    def __unicode__(self):
        return '%s %s' % (self.arrival_time,self.stop.stop_name)
    
        
class Shape(GTFSModel):
    filename = "shapes.txt"
    shape_id = models.CharField(max_length=100,db_index=True)
    shape_pt_lat = models.FloatField()
    shape_pt_lon = models.FloatField()
    shape_pt_sequence = models.IntegerField()
    def __unicode__(self):
        return '%s : lon=%s lat=%s' % (self.shape_id,self.shape_pt_lat,self.shape_pt_lon) 
    
class ShapeJson(models.Model):
    shape_id = models.CharField(max_length=100,db_index=True)
    points = models.TextField()
    
    
    
