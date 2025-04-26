import logging
import json
from pythonjsonlogger import jsonlogger

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Create a dictionary from the log record
        log_record = {
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'funcName': record.funcName,
            'created': self.formatTime(record, self.datefmt),
        }
        # Convert the dictionary to a JSON string
        return json.dumps(log_record)

def create_logger(level='ERROR', logger_name='my_logger'):    
    # Create a logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Create a console handler with a simple formatter
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Create a file handler with a detailed formatter
    file_handler = logging.FileHandler('app.log')
    # file_formatter = jsonlogger.JsonFormatter()
    file_formatter = JSONFormatter()
    file_handler.setFormatter(file_formatter)

    # Add both handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return(logger)