#!/bin/bash
source %(HOME)s/opentrain/bin/activate
exec gunicorn -p %(HOME)s/opentrain.id \
    -b 127.0.0.1:9000 \
    -w 3 opentrain.wsgi:application
 


