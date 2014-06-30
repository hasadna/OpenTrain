from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
    url(r'^search-in/$',views.TimeTableSearchIn.as_view(),name='search-in'),   
    url(r'^maps/(?P<trip_id>\w+)/',views.show_map,name='show-map'), 
)



