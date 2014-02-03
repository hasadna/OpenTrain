from django.http.response import HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import models
import json

# Create your views here.

@csrf_exempt
def add(req):
    if req.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=["POST"],content="405 - ONLY POST")
    
    body = req.body
    text = json.dumps(json.loads(body))
    rep = models.RawReport(text=text)
    rep.save()
    import analysis.logic
    analysis.logic.analyze_single_raw_report(rep)
    return HttpResponse(status=201,content="report accepted")

def show(req):
    count = int(req.GET.get('count',20))
    rrs = list(models.RawReport.objects.order_by('-id'))[0:count-1]
    total = models.RawReport.objects.count()
    data = dict(rrs=rrs,total=total)
    return render(req,'reports/results.html',data)

