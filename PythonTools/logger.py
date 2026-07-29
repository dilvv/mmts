#!/usr/bin/env python3
import logging
from logging.handlers import RotatingFileHandler
import re

import os

def in_debug_mode():
    if 'DEBUG_MODE' in os.environ:
        print("DEBUG_MODE environment variable exists.")
        return True
    else:
        return False


class SocketIOHandler(logging.Handler):
    # rst
    # .. class:: SocketIOHandler(logging.Handler)
    # 
    #    A custom logging handler that emits log messages to connected Socket.IO clients.
    # 
    #    :param socketio: The Socket.IO instance to emit messages to.
    #    :param event: The event name to emit the log messages under (default is 'server_message').
    # 
    #    .. method:: __init__(socketio, event='server_message')
    # 
    #       Initializes the SocketIOHandler with the given Socket.IO instance and event name.
    # 
    #    .. method:: emit(record)
    # 
    #       Emits a log record to all connected clients.
    # 
    #       :param record: The log record to be emitted.
    #       :raises: None
    # 
    #       This method formats the log record and emits it to the specified event for all connected clients.
    #       It also prints 'emitting' to the console for debugging purposes.

    def __init__(self, socketio, event='server_message'):
        super().__init__()
        self.socketio = socketio
        self.event = event

    def emit(self, record):
        log_entry = self.format(record)
        # emit the log to all connected clients (use broadcast=True if needed)
        self.socketio.emit(self.event, log_entry)
        print('emitting')


def generate_log_filename(filenameTEMPLATE:str):
	# .. function:: generate_log_filename(filenameTEMPLATE: str)

	# This function receives a formatted string (f-string) of a filename. 
	# It evaluates local variables and returns the formatted filename.

	# :param filenameTEMPLATE: A string template for the filename.
	# :return: A string representing the formatted filename with the current timestamp.

	# **Example:**

	# .. code-block:: python

	# 	log_filename = generate_log_filename("logfile_{TIMESTAMP}.txt")
	# 	print(log_filename)  # Output: logfile_2023-10-01_123456.txt (example output)

    from datetime import datetime
    TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    return filenameTEMPLATE.format( **locals() )
def generate_log_filename2(tag: str):
    '''
    this function receive a tag and append timestamp and generate a log file name
    '''
    from datetime import datetime
    TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"log_{tag}_{TIMESTAMP}.txt"


def testfunc_generate_log_filename():
    print(generate_log_filename('hiii'))


def jobname_in_line(jobNAME, line):
    # Check if a given job name appears in square brackets within a line of text.

    # This function searches for patterns like `[jobNAME - something]` in the input string.
    # It uses a regular expression to detect whether the given job name is followed by any characters (excluding brackets) within square brackets.

    # Parameters
    # ----------
    # jobNAME : str
    #     The job name to look for (e.g., 'myJob').
    # line : str
    #     The input line of text to search (e.g., 'askdjl [myJob - InvalidName] The detail is invalid').

    # Returns
    # -------
    #     True or False

    # Examples
    # --------
    # >>> jobname_in_line('myJob', 'askdjl [myJob - InvalidName] The detail is invalid')
    # True

    # >>> jobname_in_line('anotherJob', 'askdjl [myJob[laksdf] - InvalidName] The detail is invalid')
    # False
    # input_string = 'askdjl [myJob - InvalidName] The detail is invalid'
    import re
    pattern = fr'\[{jobNAME}(?:[^\[\]]*)\]'

    match = re.search(pattern, line)
    return True if match else False


def testfunc_jobname_in_line():
    correct_string = 'askdjl [myJob - InvalidName] The detail is valid'
    problem_string = 'askdjl [myJob[laksdf] - InvalidName] The detail is invalid'
    correct_match = jobname_in_line('myJob', correct_string)
    problem_match = jobname_in_line('myJob', problem_string)
    print(
        f'[Correct String] match result "{True if correct_match else False}" from string "{correct_string}"'
    )
    print(
        f'[Problem String] match result "{True if problem_match else False}" from string "{problem_string}"'
    )


# Custom filter class
class convertInfoToError(logging.Filter):
    # A custom logging filter that upgrades `logging.INFO` messages to `logging.ERROR`
    # if the message contains a specific job name and string pattern.

    # Parameters
    # ----------
    # jobName : str
    #     The job name to look for in the log message, e.g., "myJob".
    # filterSTR : str
    #     A substring that, when found in the message along with the job name,
    #     triggers a level upgrade to `ERROR`.

    # Example
    # -------
    # >>> import logging
    # >>> logger = logging.getLogger(__name__)
    # >>> handler = logging.StreamHandler()
    # >>> custom_filter = convertInfoToError('myJob', 'failed')
    # >>> handler.addFilter(custom_filter)
    # >>> logger.addHandler(handler)
    # >>> logger.setLevel(logging.INFO)
    # >>> logger.info("[myJob] Task failed due to timeout.")
    # [myJob] Task failed due to timeout.  # Now logged as ERROR

    def __init__(self, jobNAME, filterSTR):
        super().__init__()
        self.jobName = jobNAME
        self.filtercontent = filterSTR

    def filter(self, record):
        # Allow log messages containing "FINISHED"
        mesg = record.getMessage()
        if jobname_in_line(self.jobName, mesg) and self.filtercontent in mesg:
            record.levelname = 'ERROR'
            record.levelno = logging.ERROR
            return True
        # Otherwise, let the default level filtering take place
        return super().filter(record)


class convertInfoToWarning(logging.Filter):
    # A custom logging filter that upgrades `logging.INFO` messages to `logging.WARNING`
    # if the message contains a specific job name and string pattern.

    # Parameters
    # ----------
    # jobName : str
    #     The job name to look for in the log message, e.g., "myJob".
    # filterSTR : str
    #     A substring that, when found in the message along with the job name,
    #     triggers a level upgrade to `ERROR`.

    # Example
    # -------
    # >>> import logging
    # >>> logger = logging.getLogger(__name__)
    # >>> handler = logging.StreamHandler()
    # >>> custom_filter = convertInfoToWarning('myJob', 'failed')
    # >>> handler.addFilter(custom_filter)
    # >>> logger.addHandler(handler)
    # >>> logger.setLevel(logging.INFO)
    # >>> logger.info("[myJob] Task failed due to timeout.")
    # [myJob] Task failed due to timeout.  # Now logged as ERROR

    def __init__(self, jobNAME, filterSTR):
        super().__init__()
        self.jobName = jobNAME
        self.filtercontent = filterSTR

    def filter(self, record):
        # Allow log messages containing "FINISHED"
        mesg = record.getMessage()
        if jobname_in_line(self.jobName, mesg) and self.filtercontent in mesg:
            record.levelname = 'WARNING'
            record.levelno = logging.WARNING
            return True
        # Otherwise, let the default level filtering take place
        return super().filter(record)

STATUS_CHANGE_LEVEL = 51 # slicely higher than logging.CRITICAL
logging.addLevelName(STATUS_CHANGE_LEVEL, "StatusChange")
class convertInfoToNewLevel(logging.Filter):
    # .. class:: convertInfoToNewLevel(logging.Filter)
    # 
    #    A custom logging filter that upgrades `logging.INFO` messages to new assigned level and level number. Such as the logging.info() can be identified as a logging.error().
    # 
    #    .. method:: __init__(jobNAME: str, filterSTR: str, newLEVELname: str, newLEVELnum: int)
    # 
    #       Initializes the filter with job name, filter string, new level name, and new level number.
    # 
    #    .. method:: filter(record)
    # 
    #       Filters log records. If the message contains the specified job name and filter string, it upgrades the log level to the new assigned level and number. Otherwise, it allows the default level filtering to take place.


    def __init__(self, jobNAME:str, filterSTR:str, newLEVELname:str, newLEVELnum:int):
        #    .. method:: __init__(self, jobNAME: str, filterSTR: str, newLEVELname: str, newLEVELnum: int)
        # 
        #       :param jobNAME: The name of the job.
        #       :param filterSTR: The filter string.
        #       :param newLEVELname: The name of the new level.
        #       :param newLEVELnum: The number of the new level.

        super().__init__()
        self.jobName = jobNAME
        self.filtercontent = filterSTR
        self.newlevelname = newLEVELname
        self.newlevelnumber = newLEVELnum

    def filter(self, record):
        # Allow log messages containing "FINISHED"
        mesg = record.getMessage()
        if jobname_in_line(self.jobName, mesg) and self.filtercontent in mesg:
            record.levelname = self.newlevelname
            record.levelno = self.newlevelnumber
            return True
        # Otherwise, let the default level filtering take place
        return super().filter(record)


def create_filter(
    newtype: str,
    jobname: str,
    pattern: str,
):
    if newtype.lower() == 'error':
        return convertInfoToNewLevel(jobname, pattern, 'ERROR', logging.ERROR)
    if newtype.lower() == 'warning':
        return convertInfoToNewLevel(jobname, pattern, 'WARN ', logging.WARNING)
    if newtype.lower() == 'daqstat_idle':
        return convertInfoToNewLevel(jobname, pattern, 'StatusChangeToIdle', STATUS_CHANGE_LEVEL)
    if newtype.lower() == 'daqstat_errorclear':
        return convertInfoToNewLevel(jobname, pattern, 'StatusChangeToErrorClear', STATUS_CHANGE_LEVEL)
    raise NotImplementedError(
        f'[NotSupportType] create_filter() received type "{newtype}". The only supported types are "ERROR" and "WARNING".'
    )


def configure_logger(
    logLEVEL=logging.DEBUG,
    socketIOinst=None,
    logFILEname: str = None,
    logFILTERs: list = [],
):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Set up the logger
    logger = logging.getLogger('DAQlogger')

    logger.setLevel(logging.DEBUG if in_debug_mode() else logging.INFO)

    # Create and attach the custom handler
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")

    if socketIOinst is not None:
        socket_handler = SocketIOHandler(socketIOinst, 'server_message')
        socket_handler.setLevel(logLEVEL)
        socket_handler.setFormatter(formatter)
        for logFILTER in logFILTERs:
            socket_handler.addFilter(logFILTER)
        logger.addHandler(socket_handler)
    if logFILEname is not None:
        file_handler = RotatingFileHandler(logFILEname,
                                           maxBytes=5 * 1024 * 1024,
                                           backupCount=3)
        file_handler.setLevel(logLEVEL)
        file_handler.setFormatter(formatter)
        for logFILTER in logFILTERs:
            file_handler.addFilter(logFILTER)
        logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logLEVEL)
    stream_handler.setFormatter(formatter)
    for logFILTER in logFILTERs:
        stream_handler.addFilter(logFILTER)
    logger.addHandler(stream_handler)


def testfunc_configure_logger():
    l = logging.getLogger('DAQlogger')
    l.info("Logging without configured")

    filter_configs = (
            { 'newtype':'ERROR', 'jobname': 'job1', 'pattern': 'FINISHED' },
            { 'newtype':'ERROR', 'jobname': 'job2', 'pattern': 'No such file or directory' },
            { 'newtype':'ERROR', 'jobname': 'TestJob', 'pattern': 'log_hiii_TIMESTAMP.txt' },
            )
    configure_logger(
        logLEVEL=logging.DEBUG,
        socketIOinst=None,
        logFILEname=generate_log_filename('hiii'),
        logFILTERs=[ create_filter(**conf) for conf in filter_configs ],
    )

    l.info(
        "Logging configured but not reloaded. However, the logger applied changes"
    )
    l = logging.getLogger('DAQlogger')
    l.info(
        "Logging configured and reloaded, this message should generate a log_hiii_TIMESTAMP.txt and stdout message"
    )
    l.info(
        "[TestJob] Logging configured but not reloaded. However, the logger applied changes"
    )
    l.info(
        "[TestJob] Logging configured and reloaded, this message should generate a log_hiii_TIMESTAMP.txt and stdout message"
    )
def dict_configured_logger(
        logfile:str,
        filters:list = [],
        socketIOinst = None,
        ):
    configure_logger(
        logLEVEL=logging.DEBUG if in_debug_mode() else logging.INFO,
        socketIOinst=socketIOinst,
        logFILEname=generate_log_filename(logfile),
        logFILTERs=[ create_filter(**conf) for conf in filters ],
    )
def testfunc_dict_configure_logger():
    l = logging.getLogger('DAQlogger')
    import yaml
    with open('logger.yaml', 'r') as fIN:
        yamlCONF = yaml.safe_load(fIN)
        dict_configured_logger(**yamlCONF)


    l.info(
        "[TestJob] Logging configured but not reloaded. However, the logger applied changes"
    )
    l.info(
        "[TestJob] Logging configured and reloaded, this message should generate a log_hiii_TIMESTAMP.txt and stdout message"
    )
    

def yaml_configured_logger(yamlFILE, socketIOinst=None):
    import yaml
    with open(yamlFILE, 'r') as fIN:
        conf = yaml.safe_load(fIN)

        conf_filters = conf['filters']
        conf_logfile = conf['logfile']
    dict_configured_logger(
        logfile = conf_logfile,
        filters = conf_filters,
        socketIOinst = socketIOinst,
    )

def testfunc_yaml_configure_logger():
    l = logging.getLogger('DAQlogger')
    yaml_configured_logger('logger.yaml')


    l.info(
        "[TestJob] Logging configured but not reloaded. However, the logger applied changes"
    )
    l.info(
        "[TestJob] Logging configured and reloaded, this message should generate a log_hiii_TIMESTAMP.txt and stdout message"
    )

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='[basicCONFIG] %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')
    #testfunc_generate_log_filename()
    #testfunc_configure_logger()
    testfunc_dict_configure_logger()
    #testfunc_yaml_configure_logger()
    import testfunc
    testfunc.show_mesg()
