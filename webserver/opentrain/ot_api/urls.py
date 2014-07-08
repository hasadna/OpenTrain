from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
                       url('docs',views.show_docs,name="show_docs"),)

urlpatterns += views.ApiView.get_urls() 

    



