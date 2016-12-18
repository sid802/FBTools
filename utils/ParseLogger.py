#-*- encoding: utf-8 -*-
__author__ = 'Sidney'


import logging, os, re
from datetime import datetime

class StripStartFormatter(logging.Formatter):
    """
    Class used to remove the `new_record` part
    """

    def __init__(self, start_regex, fmt=u"%(message)s"):
        self.pattern = re.compile(u'^{0}'.format(start_regex))
        self._fmt = fmt

    def format(self, record):
        record.msg = self.pattern.sub(u'', record.msg)
        return logging.Formatter.format(self, record)

class StartFilter(logging.Filter):
    """
    Class used to filter only records that contain results
    """

    def __init__(self, start_regex):
        self.pattern = re.compile(u'^{0}'.format(start_regex))

    def filter(self, record):
        return self.pattern.match(record.msg) is not None

class LoggerManager(object):
    """
    Class meant to help managing outputs
    """

    def __init__(self, log_name, log_directory='.', encoding='utf-8'):
        self.log_name = log_name
        self.log_directory = os.path.abspath(log_directory)
        self.encoding = encoding
        self.logger = None  # Will be initiated later

    def getLogger(self):
        return self.logger

    def init_logger(self):
        """
        :return: Creates new instance, shuts down previous if still exists
        """
        if self.logger is not None:
            self.close_handlers()
        self._reset()


    def _reset(self):
        """
        :return: Reset and create new file logger
        """
        if hasattr(self, 'logger') and self.logger is not None:
            self.close_handlers()
        self.logger = self.create_new_logger(self.log_name, self.log_directory, self.encoding)

    def close_handlers(self):
        if self.logger.handlers is not None and len(self.logger.handlers) > 0:
            for handler in self.logger.handlers:
                handler.close()
                self.logger.removeHandler(handler)
        del self.logger

    class ResultsFilter(logging.Filter):
        def filter(self, record):
            return record.startswith(u'new_record')

    @staticmethod
    def create_new_logger(log_name, log_dir, encoding='utf-8'):
        """
        :param log_name: Name of log
        :param log_dir: Directory where log will be stored
        :return: Logger object correctly instantiated
        """
        now_string = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        log_results_file = os.path.join(log_dir, "results-{name}-{ts}.NEW.log".format(name=log_name, ts=now_string))
        log_general_file = os.path.join(log_dir, "full-{name}-{ts}.log".format(name=log_name, ts=now_string))

        log_format = u"%(asctime)s : %(levelname)s : %(pathname)s : %(funcName)s : %(lineno)d : %(message)s"
        results_format = u"%(message)s"
        results_start_filter = "new_record\s*"
        results_strip_start = "new_record\s*"

        logger = logging.getLogger(log_name)

        # File handler for the general logs
        general_handler = logging.FileHandler(log_general_file, encoding=encoding)
        general_format = logging.Formatter(log_format)
        general_handler.setFormatter(general_format)

        # File handler for the results logs
        results_handler = logging.FileHandler(log_results_file, encoding=encoding)
        results_format = StripStartFormatter(results_strip_start, results_format)
        results_handler.setFormatter(results_format)
        results_filter = StartFilter(results_start_filter)
        results_handler.addFilter(results_filter)

        logger.addHandler(general_handler)
        logger.addHandler(results_handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        return logger

logger = LoggerManager("FBParsing", './logs')
