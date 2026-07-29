#!/usr/bin/env python3
class JobModeStatus: # asdf
    jobmode = ''
class RunTimeStatus: # asdf
    startup = 'startup'
    initializing = 'initializing' # status when Init() is executing
    initialized = 'initialized' # status of Init() was executed

    configured = 'configured'

    running = 'running' # status of Run() is executing
    idle = 'idle' # status of Run() was executed
    stopping = 'stopping' # status of Stop() is executing
    stopped = 'stopped' # status of Stop() was executed
    destroying = 'destroying'
    destroyed = 'destroyed'
    error = 'error'




def isCommandRunable(currentSERVERstatus:str, cmdID:str):
    """
    Checks whether a command is allowed to run based on the current server status.

    This function maps a command ID to the set of allowed server statuses
    and returns a boolean indicating whether execution is permitted.

    :param currentSERVERstatus: The current status of the server.
    :type currentSERVERstatus: str
    :param cmdID: The command identifier to check. Valid options are:
                  "Init", "Configure", "Run", "Stop", "Destroy".
    :type cmdID: str
    :return: True if the command is runable in the given server status, otherwise False.
    :rtype: bool

    :Examples:

        >>> isCommandRunable("startup", "Init")
        True
        >>> isCommandRunable("idle", "Run")
        False
    """
    stat = currentSERVERstatus
    if cmdID == "Init":
        return True if stat in [ 'startup', 'destroyed' ] else False
    if cmdID == "Configure":
        return True if stat in [ 'initialized', 'stopped', 'configured', 'idle' ] else False
    if cmdID == "Run":
        return True if stat in [ 'configured' ] else False
    if cmdID == "Stop":
        return True if stat in [ 'running' ] else False
    if cmdID == "Destroy":
        #return True if stat in [ 'error', 'initializing', 'initialized', 'configured', 'running', 'idle', 'stopping', 'stopped' ] else False
        return True if stat in [ 'error', 'initialized', 'configured', 'running', 'idle', 'stopping', 'stopped' ] else False

