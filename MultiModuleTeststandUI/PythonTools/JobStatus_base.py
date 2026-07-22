#!/usr/bin/env python3
import logging
#from PythonTools.MyLogging_BashJob1 import log

log = logging.getLogger('flask.app')
#log = logging.getLogger('DAQlogger')

STAT_INERROR = -2
STAT_INVALID = -1
STAT_RUNNING =  0
STAT_FUNCEND =  1 # job is finished
STAT_BKG_RUN =  2 # job is finished but it is still background running. This means a service is opened and it stayed at background 

class JobConf:
    def __init__(self, cmdTEMPLATEs:dict, cmdARGs:dict, cmdCONSTs:dict):
        self.cmd_template = cmdTEMPLATEs
        self.cmd_args = cmdARGs
        self.cmd_consts = cmdCONSTs


    def Configure(self, newARGs:dict):
        for key, val in newARGs.items():
            if key in self.cmd_args.keys():
                self.cmd_args[key] = val
            # ignore setting not in original list
    @property
    def AllArgs(self):
        return self.cmd_args
    def GetFormattedCMD(self, cmdKEY) -> str:
        d = self.cmd_args | self.cmd_consts # | operation requiring python3p9
        try:
            return self.cmd_template[cmdKEY].format(**d)
        except KeyError as e:
            raise KeyError(f'[CMDNotFound] Command "{ cmdKEY }" is not registed in cmd_template. The available keys are "{ self.cmd_template.keys() }"') from e
        except IndexError as e:
            raise IndexError(f'\n\n[InvalidCMD] the command "{ self.cmd_template[cmdKEY]}" might be incorrected under python format() function. Please modify it. Especially for bracket {{ and }} is a reserved character\n\n') from e
    def CMDTag_and_FormattedCMD(self, cmdKEY) -> tuple:
        return cmdKEY, self.GetFormattedCMD(cmdKEY)
        
    def ValidCheck(self, *requiredCMDs):
        '''
            requiredCMDs : Put the used commands. Once the self.cmd_template does not contain these command, raise error.
        '''
        #invalid_cmd_list = [ idx if cmd not in self.cmd_template for idx,cmd in enumerate(requiredCMDs)]
        invalid_cmd_list = [ cmd for idx,cmd in enumerate(requiredCMDs) if cmd not in self.cmd_template]
        if len(invalid_cmd_list) > 0:
            log.error(f'[requiredCMDs] {requiredCMDs}')
            log.error(f'[configCMDs] {self.cmd_template.keys()}')
            log.error(f'[MissingCMD] the command "{invalid_cmd_list}" does not matched requiredCMDs')
            raise RuntimeError(f'[InvalidConfiguration] the command "{invalid_cmd_list}" used in program but not in cmd_template')

        for key,cmd_template in self.cmd_template.items():
            self.GetFormattedCMD(key)
    def Config(self, configKEY) -> str:
        return self.GetFormattedCMD(configKEY)


        

class JobStatus:
    status = 'none'
    def __init__(self,prevSTATobj=None): # as a copy constructor coping current situation
        if prevSTATobj:
            all_settings = prevSTATobj.__dict__
            for att_name in (i for i in all_settings.keys() if i[:1] != '_'):
                setattr(self, att_name, all_settings[att_name])


    def __del__(self):
        pass
    def execute(self):
        return
    def fetch_current_obj(self):
        ''' Do this function to fetch current situation. '''
        return self
    
    def Initialize(self):
        log.debug('Initialize is not allowed')
        return
    def Configure(self, theDICT):
        log.debug('Configure is not allowed')
        return
        #self.jobconf.Configure(theDICT)
    def Run(self):
        log.debug('Run is not allowed')
        return
    def Stop(self):
        log.debug('Stop is not allowed')
        return
    def Destroy(self):
        log.debug('Destroy is not allowed')
        return

