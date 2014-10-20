from django.http.response import HttpResponseNotAllowed, HttpResponse,\
    HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import models
import json

# Create your views here.

@csrf_exempt
def add(req):
    import analysis.logic
    if req.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=["POST"],content="405 - ONLY POST")
    
    body = req.body
    try:
        text = json.dumps(json.loads(body))
    except ValueError:
        return HttpResponseBadRequest(content="Could not parse json",content_type='plain/text')
    rep = models.RawReport(text=text)
    rep.save()
    cur_gtfs_trip_id = analysis.logic.analyze_single_raw_report(rep)
    content = {'cur_gtfs_trip_id': cur_gtfs_trip_id}
    return HttpResponse(status=201,content=json.dumps(content),content_type='application/json')

@csrf_exempt
def add_stop(req):
    body = req.body
    try:
        stop_info = json.loads(req.body)
    except ValueError:
        return HttpResponse(status=400,content='Wrong json format',content_type='text/plain')
    if not isinstance(stop_info,dict):
        return HttpResponse(status=400,content='Wrong json format - should be json object',content_type='text/plain')
    keys = stop_info.keys()
    extra_keys = set(keys) - {'gtfs_stop_id','latlon','device_id','bssids'}
    if extra_keys:
        return HttpResponse(status=400,content='Extra keys: %s' % list(extra_keys),content_type='text/plain')
    return HttpResponse(status=201)


def show(req):
    count = int(req.GET.get('count',20))
    rrs = list(models.RawReport.objects.order_by('-id'))[0:count-1]
    total = models.RawReport.objects.count()
    data = dict(rrs=rrs,total=total)
    return render(req,'reports/results.html',data)

