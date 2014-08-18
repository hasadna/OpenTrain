from django.middleware.common import CommonMiddleware
import urlparse
import time
import logging
class OpenTrainMiddleware(CommonMiddleware):
    def process_exception(self,request,exception):
        error_logger = logging.getLogger('opentrain.errors')
        error_logger.exception('exception in %s %s' % (request.method,request.path))
    
    def process_response(self, request, response):
        from django.db import connection
        if hasattr(request,'prof_start_time'):
            request.prof_end_time = time.time()
            total_time = request.prof_end_time - request.prof_start_time
            print '%s %s Time = %.2f DB = %d' % (request.method,
                                                 urlparse.unquote(request.get_full_path()),
                                                 total_time,
                                                 len(connection.queries))
            
        return response

    def process_request(self,request):
        request.prof_start_time = time.time()
        self.set_admin_english(request)
        
    def set_admin_english(self,req):
        from django.utils import translation
        if req.path.startswith('/admin/'):
            translation.activate('en')
            req.LANGUAGE_CODE = translation.get_language()
        

    
    
