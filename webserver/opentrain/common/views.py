from django.shortcuts import render
from django.http.response import HttpResponse

def privacy(req):
    return render(req,'common/privacy_he.html')

def home(req):
    return HttpResponse(content="hello and good day")
