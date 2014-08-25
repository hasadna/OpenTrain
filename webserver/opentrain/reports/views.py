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

def show(req):
    count = int(req.GET.get('count',20))
    rrs = list(models.RawReport.objects.order_by('-id'))[0:count-1]
    total = models.RawReport.objects.count()
    data = dict(rrs=rrs,total=total)
    return render(req,'reports/results.html',data)

