import os
import logging
from django.conf import settings

class MessageExcludeFilter(logging.Filter):
  def __init__(self, param):
    self.param = param
    
  def filter(self, record):
    return self.param not in str(record.msg)

class MessageIncludeFilter(logging.Filter):
  def __init__(self, param):
    self.param = param
    
  def filter(self, record):
    return self.param in str(record.msg)

class FilenameLineNumberExcludeFilter(logging.Filter):
  def __init__(self, filename, lineno=None):
    self.filename = filename
    self.lineno = lineno
    
  def filter(self, record):
    return self.filename not in record.filename and (not self.lineno or self.lineno != record.lineno)

# create logger
logger = logging.getLogger('algorithm')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(funcName)s %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# add file handler
#when	Type of interval
#'S'	Seconds
#'M'	Minutes
#'H'	Hours
#'D'	Days
#'W0'-'W6'	Weekday (0=Monday)
#'midnight'	Roll over at midnight
fh = logging.handlers.TimedRotatingFileHandler(os.path.join(settings.DATA_DIR, 'algorithm.log'), when='midnight') 
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# example usage:
logger.addFilter(FilenameLineNumberExcludeFilter('alg', 40))
logger.addFilter(MessageExcludeFilter('aaa'))
#logger.addFilter(FilenameLineNumberExcludeFilter('stop_detector.py'))
#logger.addFilter(FilenameLineNumberExcludeFilter('train_tracker.py', 67))
#logger.addFilter(FilenameLineNumberExcludeFilter('train_tracker.py', 118))
#logger.addFilter(FilenameLineNumberExcludeFilter('client.py', 17))
# this will get filtered out by both rules:
logger.debug('aaa')


#logger.addFilter(MessageExcludeFilter('qps'))
#logger.addFilter(MessageExcludeFilter('skipped because of large loc_ts_delta'))
#logger.addFilter(FilenameLineNumberExcludeFilter('stop_detector_test'))
#logger.addFilter(MessageIncludeFilter('No stop for bssids'))



# Filter options (from https://docs.python.org/2/library/logging.html#logrecord-attributes):
#asctime  
#%(asctime)s Human-readable time when the LogRecord was created. By default this is of the form '2003-07-08 16:49:45,896' (the numbers after the comma are millisecond portion of the time).
#created  %(created)f  Time when the LogRecord was created (as returned by time.time()).
#exc_info  You shouldn't need to format this yourself.  Exception tuple (a la sys.exc_info) or, if no exception has occurred, None.
#filename  %(filename)s  Filename portion of pathname.
#funcName  %(funcName)s  Name of function containing the logging call.
#levelname  %(levelname)s  Text logging level for the message ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
#levelno  %(levelno)s  Numeric logging level for the message (DEBUG, INFO, WARNING, ERROR, CRITICAL).
#lineno  %(lineno)d  Source line number where the logging call was issued (if available).
#module  %(module)s  Module (name portion of filename).
#msecs  %(msecs)d  Millisecond portion of the time when the LogRecord was created.
#message  %(message)s  The logged message, computed as msg % args. This is set when Formatter.format() is invoked.
#msg  You shouldn't need to format this yourself.  The format string passed in the original logging call. Merged with args to produce message, or an arbitrary object (see Using arbitrary objects as messages).
#name  %(name)s  Name of the logger used to log the call.
#pathname  %(pathname)s  Full pathname of the source file where the logging call was issued (if available).
#process  %(process)d  Process ID (if available).
#processName  %(processName)s  Process name (if available).
#relativeCreated  %(relativeCreated)d  Time in milliseconds when the LogRecord was created, relative to the time the logging module was loaded.
#thread  %(thread)d  Thread ID (if available).
#threadName  %(threadName)s  Thread name (if available).