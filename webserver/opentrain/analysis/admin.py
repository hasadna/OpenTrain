from django.contrib import admin
import common.ot_utils
import models

class ReportAdmin(admin.ModelAdmin):
    list_filter = ('device_id',)
    
admin.site.register(models.Report,ReportAdmin)

class NonEmptyTripFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = ('trip')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'trip'

    def lookups(self, request, model_admin):
        return [(x,x) for x in models.RtStop.objects.values_list('trip_id',flat=True).distinct()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(trip_id=self.value())
        return queryset


class RtStopAdmin(admin.ModelAdmin):
    list_filter = (NonEmptyTripFilter,)
    
admin.site.register(models.RtStop,RtStopAdmin)

common.ot_utils.autoregister('analysis')


