from django.contrib import admin
import common.ot_utils
import models

class ReportAdmin(admin.ModelAdmin):
    list_filter = ('device_id',)
    
admin.site.register(models.Report,ReportAdmin)

class RealTimeStopAdmin(admin.ModelAdmin):
    list_filter = ('trip')
    
admin.site.register(models.RealTimeStop,RealTimeStopAdmin)

common.ot_utils.autoregister('analysis')


