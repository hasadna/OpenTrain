from django import template
from django.utils.translation import ugettext as _

import common.ot_utils

register = template.Library()

@register.filter(name="weekday")
def week_day(dt):
    return _(common.ot_utils.get_weekdayname(dt))

@register.filter(name='timeonly')
def timeonly(dt):
    dt = common.ot_utils.get_localtime(dt)
    h = dt.hour
    m = dt.minute
    s = dt.second
    return '%02d:%02d:%02d' % (h,m,s)

@register.filter(name="nicedate")
def nice_date(dt):
    import uuid
    elemid = 'elem_%s' % (unicode(uuid.uuid4())).replace('-','')
    return '''
        <span id="%(elemid)s"></span><script>$("#%(elemid)s").html(new Date("%(isod)s").toLocaleString("he-il"))</script>
        '''  % dict(elemid=elemid,isod=dt.isoformat())
        
@register.filter(name="denorm_time")
def denorm_time(t):
    return common.ot_utils.denormalize_time_to_string(t)

@register.filter(name="direction_to_string")
def direction_to_string(d):
    if d == 0: return _('Backward')
    if d == 1: return _('Forward')
    return '???'

@register.filter(name="shapes_to_points")
def shapes_to_points(shapes):
    return "[" + ",".join(["[%s,%s]" % (shape.shape_pt_lat,shape.shape_pt_lon) for shape in shapes]) + "]"
    
@register.filter(name="truefalse")
def truefalse(val):
    return _('true') if val else _('false')

@register.filter(name="toto")
def toto(v1,v2):
    return unicode(v1) + '---' + unicode(v2)

@register.filter(name="getelem")
def getelem(idx,d):
    return d.get(idx,'---')

from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

@stringfilter
def spacify(value, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return mark_safe(esc(value).replace(' ','&nbsp;'))

spacify.needs_autoescape = True
register.filter(spacify)

