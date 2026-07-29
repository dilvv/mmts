import asyncio
import multiprocessing
import os
import signal
from PythonTools.LoggingMgr import getLogger
import logging
from JobModule.JobStatus_base import JobStatus, JobConf
from JobModule.JobStatus_base import STAT_RUNNING, STAT_BKG_RUN, STAT_FUNCEND, STAT_INVALID
from JobModule._BashCMD import bashcmd, BashJob
from JobModule._BashCMD import InitChecking as InitChecking_BashCMD
#from JobModule.JobStatus_content_example_run2bashcmd_loggers import log_bashjob1, log_bashjob9


testmode = True
used_cmds = [
    'init_bashjob1', # echo initialing
    'init_bashjob9', # for a in {{1..100}}; do echo init $a; sleep 1.0; done &

    'run_bashjob9', # for a in {{1..100}}; do echo running $a; sleep 0.4; done &

    'stop_bashjob1', # echo STOPPED

    'destroy_bashjob1', # echo DESTROYED
        ]

def InitLoggers():
    logging.getLogger('app.init_bashjob1').setLevel(logging.INFO)
    logging.getLogger('app.init_bashjob9').setLevel(logging.WARNING)

def init_job(clsCONF, flag):
    log = logging.getLogger('flask.app') # use flask app logger
    async def job_content(clsCONF, flag):
        flag.value = STAT_RUNNING

        failed_reason = InitChecking_BashCMD()
        if failed_reason:
            log.error(f'[FailChecking] InitChecking_BashCMD() reported error. Reason:\n     -> {failed_reason} <-\n\n\n')
            flag.value = STAT_INERROR
            return

        tag,cmd = clsCONF.CMDTag_and_FormattedCMD('init_bashjob1')
        if cmd:
            bashjob2 = await bashcmd(tag,cmd)
            await bashjob2.Await()



        tag,cmd = clsCONF.CMDTag_and_FormattedCMD('init_bashjob9')
        if cmd:
            log.debug(f'[init_bashjob9] got command "{cmd}"\n\n\n')
            bashjob9 = await bashcmd(tag,cmd)

            flag.value = STAT_BKG_RUN # tag this job should be running in background
            await bashjob9.Await() # this function is estimated keeping running forever
            log.debug(f'[init_bashjob9] got command "{cmd}"   EXECTION FINISHED')

        flag.value = STAT_FUNCEND


    asyncio.run(job_content(clsCONF, flag) )


def run_job(clsCONF, flag):
    async def job_content(clsCONF,flag):
        flag.value = STAT_RUNNING

        tag,cmd = clsCONF.CMDTag_and_FormattedCMD('run_bashjob9')
        if cmd:
            bashjob2 = await bashcmd(tag,cmd) # direct run
            flag.value = STAT_BKG_RUN # tag this job should be running in background
            await bashjob2.Await()
        flag.value = STAT_FUNCEND # tag this job should be running in background

    asyncio.run( job_content(clsCONF,flag) )

def stop_job(clsCONF, flag):
    async def job_content(clsCONF,flag):
        flag.value = STAT_RUNNING

        tag,cmd = clsCONF.CMDTag_and_FormattedCMD('stop_bashjob1')
        if cmd:
            bashjob1 = await bashcmd(tag,cmd)
            await bashjob1.Await()

        flag.value = STAT_FUNCEND # tag this job should be running in background

    asyncio.run( job_content(clsCONF,flag) )


def destroy_job(clsCONF, flag):
    async def job_content(clsCONF,flag):
        flag.value = STAT_RUNNING

        tag,cmd = clsCONF.CMDTag_and_FormattedCMD('destroy_bashjob1')
        if cmd:
            #bashjob1 = asyncio.create_task( bashcmd(tag,cmd) )
            bashjob1 = await bashcmd(tag,cmd)
            await bashjob1.Await()


        flag.value = STAT_FUNCEND # tag this job should be running in background

    asyncio.run( job_content(clsCONF,flag) )

def JobConfig_fromYAML(yamlCONTENT:str) -> JobConf:
    ''' usage: with open(yamlFILE,"r") as fREAD: jobconf = JobConfig_fromYAML(fREAD) '''
    import yaml
    yaml_config = yaml.safe_load(yamlCONTENT)
    return JobConf( yaml_config['cmd_templates'], yaml_config['cmd_arg'], yaml_config['cmd_const'])

def testfunc_JobConfig_fromYAML():
    yaml_content = '''
cmd_templates:
    init_bashjob1: 'echo initialing'
    init_bashjob9: 'for a in {{1..100}}; do echo init {INITvar} $a; sleep 1.0; done'

    run_bashjob9: 'for a in {{1..100}}; do echo running {RUNvar} $a; sleep 0.4; done'

    stop_bashjob1: 'echo STOPPED'

    destroy_bashjob1: 'echo DESTROYED'
cmd_arg:
    INITvar: 'this is initVar1'
cmd_const:
    RUNvar: 'this is constant variable'
'''
    return JobConfig_fromYAML(yaml_content)
