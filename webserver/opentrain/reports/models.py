from django.db import models
import json
import common.ot_utils

# Create your models here.

class RawReport(models.Model):
    text = models.TextField()
    saved_at = models.DateTimeField(auto_now_add=True,db_index=True)
    def get_text_as_dict(self):
        return json.loads(self.text)
    def get_text_nice(self):
        return json.dumps(json.loads(self.text),indent=4)
    def to_json(self):
        return dict(text=self.text,
                    id=self.id)
    def get_first_item_timestamp(self):
        items = self.get_text_as_dict()['items']
        if items:
            item = items[0]
            return common.ot_utils.get_utc_time_from_timestamp(float(item['time'])/1000)
        return None
    
        

    
    
        

    
