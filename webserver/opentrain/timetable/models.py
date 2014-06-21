from django.db import models

class Stop(models.Model):
    name = models.CharField(max_length=100)
    stop_id = models.IntegerField(db_index=True)
    stop_name = models.CharField(max_length=200)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_url = models.URLField()
    

        

