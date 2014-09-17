from django.conf.urls import patterns, url
import views
from django.conf import settings
import os.path

urlpatterns = patterns('',
    url(r'^gtfs-files/$',views.show_gtfs_files,name='show-gtfs-files'),
    url(r'^distance/$' ,views.show_distances,name='distance'),
    url(r'^old-gtfs-files/(?P<path>.*\.zip)$','django.views.static.serve',
        {'document_root' : os.path.join(settings.BASE_DIR,'tmp_data')}),
    url(r'^search-in/$',views.TimeTableSearchIn.as_view(),name='search-in'),   
    url(r'^maps/(?P<gtfs_trip_id>\w+)/',views.show_map,name='show-map'), 
)

(r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': '/path/to/media'}),

 
