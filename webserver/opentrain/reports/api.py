from tastypie.resources import ModelResource
from tastypie import fields
import models
import json

class RawReportResource(ModelResource):
    def dehydrate(self, bundle):
        bundle.data['text'] = json.loads('{"a": 100}')
        return bundle
    class Meta:
        queryset = models.RawReport.objects.all()
        resource_name = 'raw-reports'
        
def register_all(tp):
    tp.register(RawReportResource())
    
    
    