import os
import subprocess
import json
import datetime
from django.conf import settings
os.environ['DJANGO_SETTINGS_MODULE']='opentrain.settings'

if True:
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'data', 'bssids_to_stops.json'), 'r') as f:
        stop_data = json.load(f)
    data = {}
    for x in stop_data:
        data[x[0]] = []
    for x in stop_data:
        data[x[0]].append(x[2])
        
    results = {}
    for key in data:
        bssids_strings = []
        for bssid in data[key]:
            bssids_strings.append('{"macAddress": "%s"}' % bssid)
        command = "curl -XPOST -H \"Content-Type: application/json\" https://location.services.mozilla.com/v1/geolocate?key=test -d '{\"wifiAccessPoints\": [%s]}'" % ', '.join(bssids_strings)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        print "key: ", key
        print "output: ", out
        print ""
        results[key] = out
    print 'almost done'
    with open(str(datetime.datetime.now()) + 'results.txt', 'w') as f:
        json.dump(results, f)  
        
        
else:
    with open(os.path.join(settings.BASE_DIR, 'algorithm', 'stop_data.json'), 'r') as f:
        stop_data = json.load(f)
    keys = stop_data.keys()
    values = stop_data.values()
    keys = [x.replace(":", "").lower() for x in keys]
    stop_data = dict(zip(keys, values))    

    results = {}
    for key in stop_data:
        command = "curl -XPOST -H \"Content-Type: application/json\" https://location.services.mozilla.com/v1/geolocate?key=test -d '{\"wifiAccessPoints\": [{\"macAddress\": \"%s\"}]}'" % key
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        print "key: ", key
        print "output: ", out
        print ""
        results[key] = out
    with open(str(datetime.datetime.now()) + 'results.txt', 'w') as f:
        json.dump(results, f)