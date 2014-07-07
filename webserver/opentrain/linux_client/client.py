import pythonwifi
import time
import datetime
import socket
import random
import os
import json
import requests
from pythonwifi import iwlibs
from pythonwifi.iwlibs import Wireless
from subprocess import Popen, PIPE

user = 'ofer_linux'
count = 0

hostname = socket.gethostname()
while True:
    process = Popen(["iwlist", "wlan0", "scan"], stdout=PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()
    #print output    
    #print type(output)
    lines = output.split('\n')
    wifi_dict = None
    wifis = []
    for line in lines:
        if 'Cell' in line and 'Address' in line:
            if wifi_dict:
                wifis.append(wifi_dict)
            wifi_dict = {}
            wifi_dict['key'] = line[-17::]
            wifi_dict['signal'] = -1
            wifi_dict['frequency'] = -1            
        if 'ESSID' in line:
            wifi_dict['SSID'] = line.split(':')[1].strip('"')

    if wifi_dict:
        wifis.append(wifi_dict)        
    #ifnames = iwlibs.getNICnames()
    #for ifname in ifnames:
        #wifi = Wireless(ifname)
        #wifi_dict = {}
        #wifi_dict['signal'] = wifi.getTXPower()
        #wifi_dict['SSID'] = wifi.getEssid()
        #wifi_dict['frequency'] = wifi.getFrequency()
        #wifi_dict['key'] = wifi.getAPaddr().replace(':', '').lower()
        #wifis.append(wifi_dict)
    item = {}
    item['app_version_name'] = 'LinuxClient_v1'
    item['app_version_code'] = 1
    item['time'] = int(time.time() * 1000)
    shifted_date = (datetime.datetime.now() - datetime.timedelta(hours=5)).strftime("%d/%m/%Y")
    seed = hostname + '_' + shifted_date
    random.seed(seed)
    item['device_id'] = user + '_' + str(random.randint(0, 10**10))
    item['wifi'] = wifis
    body = {}
    body['items'] = []
    body['items'].append(item)
    
    body = json.dumps(body)
    print body
    headers = {'content-type':'application/json'}
    url = 'http://opentrain.hasadna.org.il/reports/add/?key=MY_HASADNA_API_KEY'
    resp = requests.post(url, headers=headers, data=body)
    if resp.status_code >= 400:
        print 'failed with: ' + resp.content
        with open('error.html','w') as fh:
            fh.write(resp.content)
        sys.exit(1)

    count += 1
    print 'sent report', count  
    time.sleep(3)     
    
    #"items": [
            #{
                #"app_version_name": "0.7.6", 
                #"wifi": [
                    #{
                        #"signal": -89, 
                        #"frequency": 2412, 
                        #"SSID": "Bartals", 
                        #"key": "0026f250e1b8"
                    #}
                #], 
                #"device_id": "f752c40d"
            #}]
    