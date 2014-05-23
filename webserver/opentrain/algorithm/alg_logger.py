import logging

class MessageFilter(logging.Filter):
  def __init__(self, param):
    self.param = param
    
  def filter(self, record):
    return self.param not in record.msg

class FilenameLineNumberFilter(logging.Filter):
  def __init__(self, filename, lineno=None):
    self.filename = filename
    self.lineno = lineno
    
  def filter(self, record):
    return self.filename not in record.filename or (not self.lineno or self.lineno != record.lineno)

# create logger
logger = logging.getLogger('algorithm')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t %(filename)s:%(lineno)d %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


# example usage:
logger.addFilter(FilenameLineNumberFilter('alg', 40))
logger.addFilter(MessageFilter('aaa'))
# this will get filtered out by both rules:
logger.debug('aaa')