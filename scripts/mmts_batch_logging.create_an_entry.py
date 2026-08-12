#!/usr/bin/env python3

# -*- coding: utf-8 -*-

from optparse import OptionParser
import time
from datetime import datetime, timezone
import os, sys
import numpy as np
import yaml
import psycopg2
import logging
import sys
from collections import deque

log = logging.getLogger(__name__)

PROGRAM_ACTIVATE_TIME = datetime.now()



ALLOWED_DESCRIPTION = [
    'test',         ### test
    'MMTSenvChecking',   ### monitoring the status of environmental chamber
    'MMTSenvAcquired',   ### MMTS check environment status before every run. Use **status_safety_alarm** for illustrating good or not
    'MMTSenvWaitNewPLCStat', ### MMTS check environment status before every run. Use **status_safety_alarm** for illustrating good or not

    'MMTSjobRunning',### MMTS is activating job.
    'MMTSjobFinished', ### MMTS finished job
    'IVSCANRun',        ###
    'IVSCANEnd',
    'PEDESTALRun',
    'PEDESTALEnd',

    'CMDInitialize',
    'CMDConfigure',
    'CMDRun',
    'CMDStop',
    'CMDDestroy',
        ]


def SQLvar_tuple(inINST:tuple) -> str:
    if isinstance(inINST,tuple) or isinstance(inINST,list):
        return 'ARRAY'+str(inINST)
    raise IOError(f'[InvalidType] inst has invalid type "{type(inINST)}"')
def SQLvar_str(inINST:str) -> str:
    ### add quote to string
    if inINST == '':
        return SQLvar_None()
    return f"'{inINST}'"
def SQLvar_None() -> str:
    return 'NULL'
def SQLvar_number(inINST) -> str:
    return inINST

def SQLvarConv(inINST) -> str:
    if inINST == None:
        return SQLvar_None()
    try:
        ### try to convert string to numbers.
        if isinstance(inINST,str):
            float(inINST)
            return SQLvar_number(inINST)
    except ValueError:
        pass
        
    if isinstance(inINST,int):
        return SQLvar_str(inINST)
    if isinstance(inINST,tuple) or isinstance(inINST,list):
        return SQLvar_tuple(inINST)
    if isinstance(inINST,str):
        return SQLvar_str(inINST)

    raise NotImplementedError(f'[UndefinedConversion] inst "{inINST}" cannot correctly convert to SQL variable for SQL insert command')

        

class insert_entry:
    column_names = {
        'batch_name': SQLvar_None(),    # string
       #'log_timestamp': PROGRAM_ACTIVATE_TIME, # timestamp
        'log_timestamp': 'now()', # timestamp
        'description': SQLvar_None(),   # string
        'module_names': SQLvar_None(),  # list of module ID
        'station_names': SQLvar_None(), # list of station name like [ 'MMTS_1L', 'testing' ]
       #'timestamp_utc': PROGRAM_ACTIVATE_TIME.astimezone(timezone.utc),
        'timestamp_utc': "now() AT TIME ZONE 'UTC'",
        'cycle_count': SQLvar_None(),   # direct decoded from iteration. get number from interation but set NULL to testing
        'status_safety_alarm': SQLvar_None()
        }
    def __init__(self, **argDICT):
        for argname, argval in argDICT.items():

            ### only accept pre-defined column
            if argname not in self.column_names:
                raise IOError(f'[InvalidArugment] argument "{argname}" is not allowed')

            ### only accept pre-defined description
            if argname == 'description':
                if argval not in ALLOWED_DESCRIPTION:
                    raise IOError(f'[InvalidDesc] description "{argval}" is invalid. Available descs: {ALLOWED_DESCRIPTION}')

            self.column_names[argname] = SQLvarConv(argval)
        self.entry_availability_check()

    def entry_availability_check(self):
        for column_name in [ 'batch_name', 'description' ]:
            if self.column_names[column_name] == SQLvar_None():
                raise IOError(f'[EmptyValueNotAllowed] column "{column_name}" is required. Current columns: "{self.column_names}"')

        

    def sql_query(self):
        all_column_names = ', '.join(self.column_names.keys  ())
        all_column_vals  = ', '.join(self.column_names.values())
        return f'''
INSERT INTO public.mmts_batch_logging
({all_column_names})
VALUES
({all_column_vals});
'''



def decode_stationname_moduleID(argSTR:str) -> tuple:
    ''' MMTS_1L:moduleID1  --> (MMTS_1L,moduleID1) '''
    if not isinstance(argSTR, str):
        raise IOError(f'[InvalidArgType] argurment required "string" type, input argSTR is "{type(argSTR)}" type.')
    if ':' not in argSTR:
        log.warning(f'[Ignored] no ":" in argument "{argSTR}". Ignore this argument.')
        return ( '', '' )
        #raise IOError(f'[FailedDecoding] input string "{argSTR}" cannot be corrected decoded')
    
    dd = argSTR.split(':')
    stationname = dd[0]
    moduleID = dd[1] if len(dd) > 1 else ''
    return (stationname, moduleID)

def decode_iteration_to_cyclecount(iterSTR:str) -> int:
    ''' iteration_1 --> 1 or cycle-1 --> 1 '''
    try:
        if '_' in iterSTR:
            return int(iterSTR.split('_')[-1])
        if '-' in iterSTR:
            if iterSTR != '-1':
                return int(iterSTR.split('-')[-1])
        nword = len(iterSTR)
        has_digit = False
        while nword > 0:
            nword -= 1
            if iterSTR[nword].isdigit():
                has_digit = True
            else:
                ## once first non-digit character found, return the digit. If no any digit, go to next session
                if has_digit:
                    return int(iterSTR[nword+1:])
                else:
                    break

        
    except ValueError as e:
        raise ValueError(f'[FailedDecoding] iteration "{iterSTR}" cannot be corrected decoded')
    if 'test' in iterSTR:
        return -1 ## if test set
    log.warning(f'[FailedDecoding] iteration "{iterSTR}" cannot be corrected decoded. Return -1')
    return -1 ## if iteration not set
        

    




def Option_Parser(argv):

    usage='usage: %prog [options] arg\n'
    parser = OptionParser(usage=usage)

    parser.add_option('-D', '--description',
            type='str', dest='description', default='',
            help=f'description for this entry, only "{ALLOWED_DESCRIPTION}" allowed'
    )
    parser.add_option('-I', '--iteration',
            type='str', dest='iteration', default='test',
            help='iteration of thermal cycling. ex: stage_1, stage_2, stage_3, testing'
    )
    parser.add_option('-S', '--stations_and_modules',
            type='str', dest='stations_and_modules', default='',
                      help='station name and module ID pair list, they are separated as comma. Ex: MMTS_1L:moduleID1,MMTS_1C:moduleID2,MMTS_1R:, The empty module ID would be ignored.'
    )
    parser.add_option('-B', '--batch',
            type='str', dest='batch', default=PROGRAM_ACTIVATE_TIME.strftime('%Y%m%d-%H%M%S'),
            help='Time stamp to start a batch of IV scan. The format would be YYYYMMDD-HHMMSS'
    )
    parser.add_option('-c', '--config',
            type='str', dest='config', default='../data/mmts_configurations.yaml',
            help='Time stamp to start a batch of IV scan. The format would be YYYYMMDD-HHMMSS'
    )


    (options, args) = parser.parse_args(argv)

    if options.description == '' or options.description not in ALLOWED_DESCRIPTION:
        log.warning(f'[InvalidDescription] description "{options.description}" is invalid. allowed options: {ALLOWED_DESCRIPTION}')
        parser.print_help()
        exit(0)

    ### decode stations_and_modules
    module_IDs = []
    station_names = []
    for station_module_pair in options.stations_and_modules.split(','):
        stationname, moduleID = decode_stationname_moduleID(station_module_pair)
        if moduleID == '':
            continue
        station_names.append(stationname)
        module_IDs.append(moduleID)
    options.station_names = station_names
    options.module_IDs = module_IDs

    ### decode cycle count from iterations
    options.cycle_count = decode_iteration_to_cyclecount(options.iteration)
    return options


class LoadConf:
    ##### load config. ###
    ''' content of configuration.yaml
### used for run.IVscan.sh
MMTS_hardwares:
  keithley:
    Resource: ASRL/dev/DAQrs232_keithley::INSTR
    Terminal: Rear
    WiresPolarization: Reverse

## configs in run.IVscan.sh
DBDatabase: 'hgcdb'
DBHostname: '192.168.50.213'
DBPassword: ''
DBUsername: 'postgres'
inspector: NTULab
    '''
    def __init__(self,confFILE):
        with open(confFILE, 'r') as fin:
            conf = yaml.safe_load(fin)
        self.DBDatabase = conf['DBDatabase']
        self.DBHostname = conf['DBHostname']
        self.DBPassword = conf['DBPassword']
        self.DBUsername = conf['DBUsername']




def testfunc():

   #options = Option_Parser(sys.argv[1:])

    conf = LoadConf('../data/mmts_configurations.yaml')
    



    testdata = insert_entry(
        batch_name = '20260723-112455', ### put this string from external MMTS GUI
        description = 'test',
        module_names = [ '320TESTMODULEID001','320TESTMODULEID002' ],
        station_names = [ 'MMTS_1L', 'MMTS_1C' ],
        cycle_count = '2'

    )

    ##########################################
    #                 Database               #
    ##########################################




    # Connect to database
    with psycopg2.connect(
        dbname   = conf.DBDatabase,
        user     = conf.DBUsername,
        password = conf.DBPassword,
        host     = conf.DBHostname,
        port     = 5432
    ) as connection:
        with connection.cursor() as cursor:
            insert_query = testdata.sql_query()
            log.debug(f'[SQLCMD] insert_query = \n{insert_query}\n')
            cursor.execute(insert_query)
            connection.commit()
def mainfunc():
    options = Option_Parser(sys.argv[1:])

    conf = LoadConf(options.config)

    sql_entry = insert_entry(
        batch_name = options.batch,
        description = options.description,
        module_names = options.module_IDs,
        station_names = options.station_names,
        cycle_count = options.cycle_count,
    )



    ##########################################
    #                 Database               #
    ##########################################





    # Connect to database
    with psycopg2.connect(
        dbname   = conf.DBDatabase,
        user     = conf.DBUsername,
        password = conf.DBPassword,
        host     = conf.DBHostname,
        port     = 5432
    ) as connection:
        with connection.cursor() as cursor:
            insert_query = sql_entry.sql_query()
            cursor.execute(insert_query)
            connection.commit()



if __name__ == '__main__':
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
            format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
            datefmt='%H:%M:%S')

    mainfunc()
   #testfunc()



