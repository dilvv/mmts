import asyncio
import multiprocessing
import threading
import signal
#import logging
from JobModule.JobStatus_base import JobStatus, JobConf
from JobModule.JobStatus_base import STAT_RUNNING, STAT_BKG_RUN, STAT_FUNCEND, STAT_INVALID, STAT_INERROR
import logging
log = logging.getLogger('flask.app')
#log = logging.getLogger('DAQlogger')
## deprecated args: funcpool,

from JobModule._BashCMD import bashcmd, BashJob


def run_command(cmd: str, jobID):
    """
    Executes a shell command in a subprocess, monitors its output line by line,
    and logs status messages including stop signals and errors.

    This function is designed to integrate with a server job control system.
    If a global ``job_stop_flags`` is set, the subprocess is terminated gracefully.
    It also updates the server status using ``set_server_status()`` and logs each
    step of execution.

    :param cmd: The shell command to run.
    :type cmd: str
    :param jobID: Identifier for the job, used in log messages.
    :type jobID: any
    :return: None
    :raises Exception: Logs any unexpected exception occurring during command execution.

    :Side Effects:
        - Starts a subprocess with ``cmd``.
        - Logs output line by line.
        - Terminates the subprocess if ``job_stop_flags`` is set.
        - Calls ``set_server_status()`` to manage server state transitions.

    :Logging:
        - Logs command start, each output line, stop signals, errors, and completion.
    """
    logger.info(f"[RunBashCMD][{jobID}] run_command executes command: {cmd}")
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        for line in process.stdout:
            logger.info(f'[{jobID}{line.strip()}')

            if job_stop_flags[jobID].is_set():
                logger.info(f"[{jobID}][Stop - Terminate]run_command() Stop signal received. Terminating command.")
                process.terminate()
                logger.info(f"[{jobID}][Stop - Terminate]run_command() process terminate sent.")
                break
        if not job_stop_flags[jobID].is_set():
            logger.info(f'[{jobID}][Run - StatusChangeIdle]run_command() Command "{cmd}" finished')
    except Exception as e:
        logger.error(f'[{jobID}][Error - StatusChangeError]run_command() Error while running command: "{cmd}"')

        process.terminate()
        if server_status_is('stopping'):
            logger.info(f'[{jobID}][Error - StatusChangeError]run_command() error generated sinces "Stop" button clicked')
        else:
            logger.error(f'[{jobID}][Error - ErrorMessage     ] run_command() "{e}"')
    finally:
        process.wait()
        set_server_status('idle')
        logger.info(f'[{jobID}][finally] run_command() sets system to idle')


def destroy_process(clsOBJ, processNAME):
    if hasattr(clsOBJ, processNAME):
        process = getattr(clsOBJ, processNAME)
        process.terminate()
        process.join()  # Ensure the process stops
        delattr(clsOBJ, processNAME)
def destroy_flag(clsOBJ, flagNAME):
    if hasattr(clsOBJ, flagNAME):
        delattr(clsOBJ, flagNAME)



class JobStatus_JobSelect(JobStatus):
    status = 'job_select'
    def __init__(self):
        pass

    def Factory(self, jobMODE):
        return JobStatusFactory(jobMODE)
        



class JobStatus_Startup(JobStatus):
    status = 'startup'
    def __init__(self, funcPOOL, jobCONF:JobConf):
        super().__init__(None)
        self.func_pool = funcPOOL
        #self.bkgjob_init_flag = multiprocessing.Value('i', STAT_INVALID)
        self.bkgjob_init_flag = STAT_INVALID
        jobCONF.ValidCheck(*self.func_pool.used_cmds)
        self.config = jobCONF
    def fetch_current_obj(self):
        if self.bkgjob_init_flag < 0:
            log.debug(f'[StayCurrentObj] Keeps status "{self.status}"')
            return self
        log.debug(f'[NewObj] Move to new object "JobStatus_Initializing". Initializing object from JobStatus_Startup')
        return JobStatus_Initializing(self)

    def Initialize(self):
        log.debug(f'[InitializeCMD] Initializing current job from status "{ self.status }"')
        if self.bkgjob_init_flag != STAT_INVALID:
            log.debug(f'[Initializing] The job is initializing ... Please use fetch_current_obj() to fetch current object')
            return
        
        self.bkgjob_init_process = multiprocessing.Process(target=self.func_pool.init_job, args=(self.config, self.bkgjob_init_flag))
        self.bkgjob_init_process.start()

def testfunc_JobStatus_Startup():
    job = JobStatus_Startup(jobtest, thejobconf) # to be recovered
    job.Initialize()
    #job.Run()
    input("Put enter to stop all program\n\n")
    log.debug(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
    job = job.fetch_current_obj()
    log.debug(job)
    input("Put enter to stop all program\n\n")
    log.debug(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
    job = job.fetch_current_obj()
    log.info(job)
    input("Put enter to stop all program\n\n")
    log.debug(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
    job = job.fetch_current_obj()
    log.debug(job)
    job.bkgjob_init_process.terminate()
    job.bkgjob_init_process.join()


class JobStatus_Initializing(JobStatus):
    status = 'initializing'
    def __init__(self, prevSTATobj):
        super().__init__(prevSTATobj)
        if not hasattr(self, 'bkgjob_init_flag'   ):
            log.error('[InvalideObject] JobStatus_Initializing() requires class attribute "bkgjob_init_flag" in __init__()')
        if not hasattr(self, 'bkgjob_init_process'):
            log.error('[InvalidObject] JobStatus_Initializing() requires class attribute "bkgjob_init_process" in __init__()')
    def fetch_current_obj(self):
        if not hasattr(self, 'bkgjob_init_flag'):
            log.error(f'[RuntimeError] no running initializing job in JobStatus_Initializing() object')
            return JobStatus_Error(self)

        if self.bkgjob_init_flag <= STAT_INERROR:
            log.error('[InitializeError] Initialize() process raised error.')
            return self

        if self.bkgjob_init_flag <= 0:
            log.debug(f'[StayCurrentObj] Keeps status "{self.status}"')
            return self
        log.debug(f'[NewObj] Move to new object "JobStatus_Initialized". Initialize() finished.')
        return JobStatus_Initialized(self)
        
    def Destroy(self):
        log.debug(f'[DestroyCMD] Destroying from status "{ self.status }"')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )
        destroy_process(self, 'bkgjob_init_process')
        destroy_flag   (self, 'bkgjob_init_flag'   )

        #self.destroy_flag = multiprocessing.Value('i', STAT_INVALID)
        self.destroy_flag = STAT_INVALID
        self.destroy_process = multiprocessing.Process(target=self.func_pool.destroy_job, args=(self.config, self.destroy_flag))
        self.destroy_process.start()
        self.destroy_process.join()
        delattr(self, 'destroy_flag')
        delattr(self, 'destroy_process')

class JobStatus_Initialized(JobStatus):
    status = 'initialized' # Initialized is equal to Idle
    def __init__(self, prevSTATobj):
        super().__init__(prevSTATobj)
        if not hasattr(self, 'bkgjob_init_flag'   ): raise RuntimeError('[InvalidObject] JobStatus_Initializing() requires class attribute "bkgjob_init_flag"')
        if not hasattr(self, 'bkgjob_init_process'): raise RuntimeError('[InvalidObject] JobStatus_Initializing() requires class attribute "bkgjob_init_process"')
        self.configured = False
    def execute(self):
        pass
    def fetch_current_obj(self):
        if not hasattr(self, 'bkgjob_init_flag'):
            log.debug(f'[ObjectDestroyed] Move object to JobStatus_JobSelect')
            return JobStatus_JobSelect()

        if not self.configured:
            log.debug(f'[StayCurrentObj] Keeps status "{self.status}"')
            return self
        delattr(self, 'configured')
        log.debug(f'[NewObj] Move to new object "JobStatus_Configured". Need to use Configure() put runtime information')
        return JobStatus_Configured(self)
        
    def Configure(self, confDICT):
        log.debug(f'[ConfigureCMD] set runtime variable to arguments from status "{ self.status }"')
        self.config.Configure(confDICT)
        log.info(f'\n\n\n\n\n\nJobStatus_main :: {self.config.AllArgs}\n\n\n\n\n\n') # asdf
        self.configured = True

    def Destroy(self):
        log.debug(f'[DestroyCMD] Destroying from status "{ self.status }"')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )
        destroy_process(self, 'bkgjob_init_process')
        destroy_flag   (self, 'bkgjob_init_flag'   )

        #self.destroy_flag = multiprocessing.Value('i', STAT_INVALID)
        self.destroy_flag = STAT_INVALID
        self.destroy_process = multiprocessing.Process(target=self.func_pool.destroy_job, args=(self.config, self.destroy_flag))
        self.destroy_process.start()
        self.destroy_process.join()
        delattr(self, 'destroy_flag')
        delattr(self, 'destroy_process')



class JobStatus_Configured(JobStatus):
    status = 'configured'
    def __init__(self, prevSTATobj):
        super().__init__(prevSTATobj)
        #self.bkgjob_main_flag = multiprocessing.Value('i', STAT_INVALID)
        self.bkgjob_main_flag = STAT_INVALID
    def fetch_current_obj(self):
        if not hasattr(self, 'bkgjob_init_flag'):
            log.debug(f'[ObjectDestroyed] Move object to JobStatus_JobSelect')
            return JobStatus_JobSelect()

        if self.bkgjob_main_flag == STAT_INVALID:
            log.debug(f'[StayCurrentObj] Keeps status "{self.status}"')
            return self
        log.debug(f'[NewObj] Move to new object "JobStatus_Running". run time configuration finished')
        return JobStatus_Running(self)

    def Configure(self, confDICT):
        log.debug(f'[ConfigureCMD] set runtime variable to arguments from status "{ self.status }"')
        self.config.Configure(confDICT)
        log.info(f'\n\n\n\n\n\nJobStatus_main :: {self.config.AllArgs}\n\n\n\n\n\n') # asdf
        return  # JobStatus_Configured would not generate another JobStatus_Configured object
    def Run(self):
        log.debug(f'[RunCMD] Running current job from status "{ self.status }"')
        if self.bkgjob_main_flag != STAT_INVALID:
            log.warning(f'[Initializing] The job is initializing ... Please use fetch_current_obj() to fetch current object')
            return
        
        #main_job(self.config, self.bkgjob_main_flag)
        self.bkgjob_main_process = multiprocessing.Process(target=self.func_pool.run_job, args=(self.config, self.bkgjob_main_flag))
        self.bkgjob_main_process.start()
        
    def Destroy(self):
        log.debug(f'[DestroyCMD] Destroying from status "{ self.status }"')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )
        destroy_process(self, 'bkgjob_init_process')
        destroy_flag   (self, 'bkgjob_init_flag'   )

        #self.destroy_flag = multiprocessing.Value('i', STAT_INVALID)
        self.destroy_flag = STAT_INVALID
        self.destroy_process = multiprocessing.Process(target=self.func_pool.destroy_job, args=(self.config, self.destroy_flag))
        self.destroy_process.start()
        self.destroy_process.join()
        delattr(self, 'destroy_flag')
        delattr(self, 'destroy_process')

class JobStatus_Running(JobStatus):
    status = 'running'
    def __init__(self, prevSTATobj):
        super().__init__(prevSTATobj)
    def fetch_current_obj(self):
        if not hasattr(self, 'bkgjob_init_flag'):
            log.debug(f'[ObjectDestroyed] Move object to JobStatus_JobSelect')
            return JobStatus_JobSelect()

        if hasattr(self, 'bkgjob_main_flag') and getattr(self, 'bkgjob_main_flag') <= 0:
            log.debug(f'[StayCurrentObj] Keeps status "{self.status}"')
            return self

        log.debug(f'[NewObj] Move to new object "JobStatus_Initialized". Job is stopped or finished')
        return JobStatus_Initialized(self)

    def Stop(self):
        log.debug(f'[StopCMD] Stopping current job')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )

        #self.stop_flag = multiprocessing.Value('i', STAT_INVALID)
        self.stop_flag = STAT_INVALID
        self.stop_process = multiprocessing.Process(target=self.func_pool.stop_job, args=(self.config, self.stop_flag))
        self.stop_process.start()
        self.stop_process.join()
        delattr(self, 'stop_flag')
        delattr(self, 'stop_process')

    def Destroy(self):
        log.debug(f'[DestroyCMD] Destroying from status "{ self.status }"')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )
        destroy_process(self, 'bkgjob_init_process')
        destroy_flag   (self, 'bkgjob_init_flag'   )

        #self.destroy_flag = multiprocessing.Value('i', STAT_INVALID)
        self.destroy_flag = STAT_INVALID
        self.destroy_process = multiprocessing.Process(target=self.func_pool.destroy_job, args=(self.config, self.destroy_flag))
        self.destroy_process.start()
        self.destroy_process.join()
        delattr(self, 'destroy_flag')
        delattr(self, 'destroy_process')




class JobStatus_Error(JobStatus):
    status = 'error'
    def __init__(self, prevSTATobj):
        super().__init__(prevSTATobj)

    def fetch_current_obj(self):
        if hasattr(self, 'bkgjob_init_flag'   ): return self
        if hasattr(self, 'bkgjob_init_process'): return self
        if hasattr(self, 'bkgjob_main_flag'   ): return self
        if hasattr(self, 'bkgjob_main_process'): return self

        return JobStatus_JobSelect()
        
    def Destroy(self):
        log.debug(f'[DestroyCMD] Destroying from status "{ self.status }"')
        destroy_process(self, 'bkgjob_main_process')
        destroy_flag   (self, 'bkgjob_main_flag'   )
        destroy_process(self, 'bkgjob_init_process')
        destroy_flag   (self, 'bkgjob_init_flag'   )

        #self.destroy_flag = multiprocessing.Value('i', STAT_INVALID)
        self.destroy_flag = STAT_INVALID
        self.destroy_process = multiprocessing.Process(target=self.func_pool.destroy_job, args=(self.config, self.destroy_flag))
        self.destroy_process.start()
        self.destroy_process.join()
        delattr(self, 'destroy_flag')
        delattr(self, 'destroy_process')

### jobMODE is connected with
###    *  app_actbtn.btn_initialize(data)
###    *  index.html #radio-form
def JobStatusFactory(jobMODE:str):
    yaml_file = ''

    if jobMODE == 'test':
        #import JobModule.JobStatus_content_example_run2bashcmd_loggers
        import JobModule.JobStatus_content_example_run2bashcmd as jobtest
        func_pool = jobtest
        yaml_file = 'data/JobStatus_content_example_run2bashcmd.yaml'
    if jobMODE == 'pyjob_mode1':
        import JobModule.JobStatus_content_pedestalrun_with_powersupply_control as jobpedestalrun
        func_pool = jobpedestalrun
        yaml_file = 'data/JobStatus_content_pedestalrun_with_powersupply_control.yaml'
    if jobMODE == 'pyjob_mode2':
        import JobModule.JobStatus_content_pedestalrun_with_powersupply_control as jobpedestalrun
        func_pool = jobpedestalrun
        yaml_file = 'data/JobStatus_content_pedestalrun_with_powersupply_control.yaml'


    if not yaml_file:
        log.error(f'[InvalidJobModule] JobStatusFactory() got invalid job mode "{ jobMODE }"!!!')
        return None


    with open(yaml_file, 'r') as fIN:
        jobconfig = func_pool.JobConfig_fromYAML(fIN)
        return JobStatus_Startup(func_pool, jobconfig)


def testfunc_JobStatus_whole_flow():
    cmd_templates = {
    'init_bashjob1'     : 'echo hi {initVar1}',
    'init_pwrjob2'      : 'poweron',
    'init_bashjob9'     : 'echo hi 999',

    'run_pwrjob1'       : 'kkk',
    'run_bashjob9'      : 'echo jjj {constVar}',

    'stop_bashjob1'     : '',

    'destroy_pwrjob1'   : 'poweroff',
    }
    cmd_arg = {
            'initVar1': 'this is initVar1',
    }
    cmd_const = {
            'constVar': 'this is constant variable',
    }
    jobconf = JobConf(cmd_templates, cmd_arg, cmd_const)
    job = JobStatus_Startup(jobtest, jobconf)
    job.Initialize()
    input("Put enter to stop all program")
    log.info(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
    job = job.fetch_current_obj()
    while True:
        input("Put enter to stop all program")
        log.info(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
        job = job.fetch_current_obj()
        log.info(job)
        log.info('Configure--')
        job.Configure({'aaD':'cc'})
        log.info('Run--')
        job.Run()
        log.info('Stop--')
        job.Stop()

    log.info(job)
    input("Put enter to stop all program")
    log.info(f'[current status] job.bkgjob_init_flag = {job.bkgjob_init_flag}')
    job = job.fetch_current_obj()
    job.Destroy()
    log.info(job)
    job.bkgjob_init_process.terminate()
    job.bkgjob_init_process.join()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='[basicCONFIG] %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')
    #testfunc_JobStatus_Startup()
    testfunc_JobStatus_whole_flow()


