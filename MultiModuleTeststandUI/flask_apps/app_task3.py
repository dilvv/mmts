import subprocess
import threading
import logging
from flask import Flask, render_template, request, jsonify, Blueprint
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms.validators import DataRequired, Regexp, InputRequired, NumberRange
from wtforms import StringField, SubmitField, RadioField, IntegerField
import flask_apps.shared_state as shared_state
from PythonTools.batch_status import read_status
from PythonTools.server_status import isCommandRunable
import re
import os
import sys
import yaml
import signal
### HTTP status codes https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

JOBMODE = 'task3' # IV scan

andrewCONF = f'{os.environ.get("AndrewModuleTestingGUI_BASE")}/configuration.yaml'
dirDAQresult = ''
try:
    with open(andrewCONF, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        dirDAQresult = f"{conf['DataLoc']}/daqplots/"
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[NoEnvVar] Need to `source ./init_bash_vars.sh` before execute this file') from e

mmtsCONF = 'data/mmts_configurations.yaml'
external_URL = ''
external_URL_height = '200px'
try:
    with open(mmtsCONF, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        external_URL = conf['externalURL']['IVCurveOnline']['URL']
        external_URL_height = conf['externalURL']['IVCurveOnline']['height']
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[LackOfMMTSconf] Need to create configuration file "data/mmts_configuration.yaml"') from e

CONF_DICT = {
        'currentHUMIDITY': '',
        'currentTEMPERATURE': '',
       #'inspector': '',    ### not used
       #'moduleSTATUS': '', ### not used
        'moduleID1L': '',
        'moduleID1C': '',
        'moduleID1R': '',
        'moduleID2L': '',
        'moduleID2C': '',
        'moduleID2R': '',
        'moduleID3L': '',
        'moduleID3C': '',
        'moduleID3R': '',

        'moduleID4L': '',
        'moduleID4C': '',
        'moduleID4R': '',
        'moduleID5L': '',
        'moduleID5C': '',
        'moduleID5R': '',
        'moduleID6L': '',
        'moduleID6C': '',
        'moduleID6R': '',

        'moduleID7L': '',
        'moduleID7C': '',
        'moduleID7R': '',
        'moduleID8L': '',
        'moduleID8C': '',
        'moduleID8R': '',
        }

def ExecCMD(jobID:str, confDICT:dict):
    make_command = 'make -n' if shared_state.debug_mode else 'make'
    if jobID == 'Init':
        return f'{make_command} -f makefile_task3 initialize JobName=Init'
    if jobID == 'Run':
        shared_state.runidx+=1
        runTAG = f'run{shared_state.runidx}'
        dictOPTs = ' '.join([ f'{key}={val}' for key,val in confDICT.items() if val != '' ])

        ### a patch
        if int(confDICT['currentHUMIDITY']) < 12.0:
            dictOPTs += ' maxVOLTAGE=850'
        else:
            dictOPTs += ' maxVOLTAGE=500'
        ### a patch END
        return f'{make_command} -f makefile_task3 run ' + dictOPTs
    if jobID == 'Stop':
        return f'{make_command} -f makefile_task3 stop JobName=Stop'
    if jobID == 'Destroy':
        return f'{make_command} -f makefile_task3 destroy JobName=Destroy'


def module_ids_from_conf(confDICT:dict):
    return {
        key.replace('moduleID', ''): val
        for key, val in confDICT.items()
        if key.startswith('moduleID')
    }


def build_autotest_config(confDICT:dict):
    config_template = 'data/full_batch_config.example.yml'
    runtime_dir = os.path.join('tmp_files', 'runtime')
    os.makedirs(runtime_dir, exist_ok=True)
    runtime_config = os.path.join(runtime_dir, 'full_batch_web.yml')

    with open(config_template, 'r', encoding='utf-8') as fin:
        cfg = yaml.safe_load(fin)

    cfg['module_ids'] = module_ids_from_conf(confDICT)
    with open(runtime_config, 'w', encoding='utf-8') as fout:
        yaml.safe_dump(cfg, fout, sort_keys=False)
    return runtime_config


def save_config_from_json(json_data:dict, require_run_fields=True):
    if not json_data:
        return False, {'message': 'Missing JSON data'}

    form = ConfigForm(data=json_data)
    if require_run_fields and not form.validate_on_submit():
        errors = {}
        for fieldName, errorMessages in form.errors.items():
            errors[fieldName] = errorMessages
        return False, errors
    if not require_run_fields:
        for field in [
            form.moduleID1L, form.moduleID1C, form.moduleID1R,
            form.moduleID2L, form.moduleID2C, form.moduleID2R,
            form.moduleID3L, form.moduleID3C, form.moduleID3R,
            form.moduleID4L, form.moduleID4C, form.moduleID4R,
            form.moduleID5L, form.moduleID5C, form.moduleID5R,
            form.moduleID6L, form.moduleID6C, form.moduleID6R,
            form.moduleID7L, form.moduleID7C, form.moduleID7R,
            form.moduleID8L, form.moduleID8C, form.moduleID8R,
        ]:
            if not field.validate(form):
                return False, {field.name: field.errors}

    def ignore_special_characters(string):
        return re.sub(r'[^A-Za-z0-9\-]+', '', string) if string else ''

    for varname in CONF_DICT.keys():
        value = getattr(form, varname).data if hasattr(form, varname) else ''
        clean_val = ignore_special_characters(str(value))
        if len(clean_val) > 20:
            clean_val = ''
        CONF_DICT[varname] = clean_val

    is_empty_dict = sum(1 if v else 0 for _, v in CONF_DICT.items()) == 0
    if is_empty_dict:
        return False, 'Got empty configurations!'
    return True, {}



#logger = logging.getLogger('flask.app')
logger = logging.getLogger('werkzeug')


app = Blueprint('app_task3', __name__)


job_stop_flags = {
        'Init': threading.Event(),
        'Run': threading.Event(),
        'AutoTest': threading.Event(),
        'Stop': threading.Event(),
        'Destroy': threading.Event(),
        }

def bb(val):
    logger.warn(f'checking point {val}')
def check_jobmode() -> bool:
    logger.info(f'[CheckJobMode] coming jobmode {JOBMODE} and current status is {shared_state.jobmode}')
    if not shared_state.jobmode:
        logger.info(f'[ReplaceJobMode] jobmode modified from None to {JOBMODE}')
        shared_state.jobmode = JOBMODE
        return True

    if shared_state.jobmode == JOBMODE:
        logger.info(f'[CorrectJobMode] jobmode {JOBMODE} matched, keep running on')
        return True

    logger.warning(f'[InvalidJobMode] jobmode "{ shared_state.jobmode }" mismatched with local "{ JOBMODE }". Ignore command')
    return False



job_thread = {
        'Init': None,
        'Run': None,
        'AutoTest': None,
        'Stop': None,
        'Destroy': None,
        }
job_process = {
        'Init': None,
        'Run': None,
        'AutoTest': None,
        'Stop': None,
        'Destroy': None,
        }


def terminate_process(process, jobID):
    if not process or process.poll() is not None:
        return
    try:
        logger.info(f'[{jobID}][Terminate] terminating process group pid={process.pid}')
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
    except Exception as e:
        logger.warning(f'[{jobID}][Terminate] graceful termination failed: {e}')
        try:
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=5)
        except Exception as kill_error:
            logger.error(f'[{jobID}][Terminate] force kill failed: {kill_error}')


def stop_running_jobs(jobIDs):
    for jobID in jobIDs:
        if jobID in job_stop_flags:
            job_stop_flags[jobID].set()
        terminate_process(job_process.get(jobID), jobID)


def join_job_threads(jobIDs, timeout=10):
    for jobID in jobIDs:
        t = job_thread.get(jobID)
        if t and t.is_alive():
            t.join(timeout=timeout)
            if t.is_alive():
                logger.warning(f'[{jobID}][JoinTimeout] thread still alive after {timeout}s')


def set_thread(runTYPE, tHREAD:threading.Thread):
    if runTYPE not in job_thread:
        logger.warning(f'[InvalidRunType] set_thread() got run type "{runTYPE}" but only "{ job_thread.keys() }" allowed')
        logger.warning(f'[InvalidRunType] set_thread() add "{runTYPE}" in the threading pool')

    if job_thread[runTYPE] and job_thread[runTYPE].is_alive():
        #logger.warning(f'[JobIsRunning] set_thread() got running thread. overwrite this running thread')
        logger.warning(f'[JobIsRunning] set_thread() got running thread. waiting for previous thread finished')
        job_thread[runTYPE].join()

    job_thread[runTYPE] = tHREAD



def set_server_status(newSTAT):
    if shared_state.server_status == 'error': ## if error
        if newSTAT not in [ 'destroying', ]:
            return

    shared_state.server_status = newSTAT

def server_status_is(checkSTAT):
    return shared_state.server_status == checkSTAT

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
        bufsize=1,
        start_new_session=True,
    )
    job_process[jobID] = process

    try:
        for line in process.stdout:
            logger.info(f'[{jobID}{line.strip()}')

            if job_stop_flags[jobID].is_set():
                logger.info(f"[{jobID}][Stop - Terminate]run_command() Stop signal received. Terminating command.")
                terminate_process(process, jobID)
                logger.info(f"[{jobID}][Stop - Terminate]run_command() process terminate sent.")
                break
        if not job_stop_flags[jobID].is_set():
            logger.info(f'[{jobID}][Run - StatusChangeIdle]run_command() Command "{cmd}" finished')
    except Exception as e:
        logger.error(f'[{jobID}][Error - StatusChangeError]run_command() Error while running command: "{cmd}"')

        terminate_process(process, jobID)
        if server_status_is('stopping'):
            logger.info(f'[{jobID}][Error - StatusChangeError]run_command() error generated sinces "Stop" button clicked')
        else:
            logger.error(f'[{jobID}][Error - ErrorMessage     ] run_command() "{e}"')
    finally:
        process.wait()
        job_process[jobID] = None
        if process.returncode == 0:
            set_server_status('idle')
            logger.info(f'[{jobID}][finally] run_command() sets system to idle')
        else:
            set_server_status('error')
            logger.info(f'[{jobID}][error] run_command() sets system to error. Please destroy and initialize it')




@app.route('/init', methods=['POST'])
def Init():
    ''' run bash command `make initialize` at background '''
    CMD_ID = 'Init'

    #logger.debug(f'[ServerAction][Init] Got an Init command')
    current_app.logger.debug(f'------------------- [ServerAction][Init] Got an Init command')

    if not check_jobmode(): return '', 204

    if isCommandRunable(shared_state.server_status,CMD_ID):
        set_server_status('initializing')
        job_stop_flags[CMD_ID].clear()
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] the server status is idle, activate {CMD_ID} command')

        def background_worker():
            try:
                command = ExecCMD(CMD_ID, CONF_DICT)
                #current_app.logger.debug(f'[bkg CMD Init] {command}')
                run_command(command, CMD_ID)
            finally:
                shared_state.DAQresult_current_modified = ''
                set_server_status('initialized')
                logger.info("Job status set to idle.")
            logger.info('background worker ended')


        t = threading.Thread(target=background_worker)
        t.start()
        set_thread(CMD_ID, t) # put to background running
    else:
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] Current status is {shared_state.server_status}. reject "{CMD_ID}" command')

    return '', 204

alphanumeric_validator = Regexp(r"^[a-zA-Z0-9\-]*$", message="Only letters and numbers and dash allowed.")
#alphanumeric_validator = Regexp("^[a-zA-Z0-9]*$", message="Only letters and numbers allowed.")
class ConfigForm(FlaskForm):
    currentTEMPERATURE = StringField("currentTEMPERATURE", validators=[InputRequired(message='Temperature Missing')])
   #moduleSTATUS = RadioField("moduleSTATUS", validators=[InputRequired()])
    currentHUMIDITY    = IntegerField("currentHUMIDITY"   , validators=[
        NumberRange(min=0.,max=100., message='Number from 0 to 100'),
        InputRequired(message='Humidity Missing')]
                                     )

    moduleID1L = StringField("moduleID1L", validators=[alphanumeric_validator])
    moduleID1C = StringField("moduleID1C", validators=[alphanumeric_validator])
    moduleID1R = StringField("moduleID1R", validators=[alphanumeric_validator])
    moduleID2L = StringField("moduleID2L", validators=[alphanumeric_validator])
    moduleID2C = StringField("moduleID2C", validators=[alphanumeric_validator])
    moduleID2R = StringField("moduleID2R", validators=[alphanumeric_validator])
    moduleID3L = StringField("moduleID3L", validators=[alphanumeric_validator])
    moduleID3C = StringField("moduleID3C", validators=[alphanumeric_validator])
    moduleID3R = StringField("moduleID3R", validators=[alphanumeric_validator])

    moduleID4L = StringField("moduleID4L", validators=[alphanumeric_validator])
    moduleID4C = StringField("moduleID4C", validators=[alphanumeric_validator])
    moduleID4R = StringField("moduleID4R", validators=[alphanumeric_validator])
    moduleID5L = StringField("moduleID5L", validators=[alphanumeric_validator])
    moduleID5C = StringField("moduleID5C", validators=[alphanumeric_validator])
    moduleID5R = StringField("moduleID5R", validators=[alphanumeric_validator])
    moduleID6L = StringField("moduleID6L", validators=[alphanumeric_validator])
    moduleID6C = StringField("moduleID6C", validators=[alphanumeric_validator])
    moduleID6R = StringField("moduleID6R", validators=[alphanumeric_validator])

    moduleID7L = StringField("moduleID7L", validators=[alphanumeric_validator])
    moduleID7C = StringField("moduleID7C", validators=[alphanumeric_validator])
    moduleID7R = StringField("moduleID7R", validators=[alphanumeric_validator])
    moduleID8L = StringField("moduleID8L", validators=[alphanumeric_validator])
    moduleID8C = StringField("moduleID8C", validators=[alphanumeric_validator])
    moduleID8R = StringField("moduleID8R", validators=[alphanumeric_validator])
    submit = SubmitField("Configure")

@app.route('/submit', methods=['POST','GET'])
def Configure():
    CMD_ID = 'Configure'

    if not check_jobmode(): return '', 204
    if not isCommandRunable(shared_state.server_status,CMD_ID): return '', 204




    json_data = request.get_json()
    
    print('\n\n\n',json_data,'\n\n\n')
    if not json_data:
        return jsonify({'status': 'error', 'message': 'Missing JSON data'}), 400


    form = ConfigForm(data=json_data)  # populate form with JSON data



    if not form.validate_on_submit():

        # Collect validation errors
        errors = {}
        for fieldName, errorMessages in form.errors.items():
            errors[fieldName] = errorMessages
        current_app.logger.warning(f'[Configure] Validation errors: {errors}')
        return jsonify({'status': 'error', 'errors': errors}), 400


    def ignore_special_characters(string):
        return re.sub(r'[^A-Za-z0-9\-]+', '', string) if string else '' ## allow capital characters, numbers
        #return re.sub(r'[^A-Za-z0-9]+', '', string) if string else '' ## allow capital characters, numbers and dash


    # Update CONF_DICT only if field has data
    form_vars = vars(form).keys()

    current_app.logger.debug(f'[LoadFormFromClient] Form "{vars(form)}"')

    for varname in CONF_DICT.keys():
        value = getattr(form, varname).data if hasattr(form, varname) else ''
        current_app.logger.debug(f'[GotValue] Form {varname} got original value "{value}"')
        clean_val = ignore_special_characters(str(value))
        if len(clean_val) > 20:
            current_app.logger.warning(f'[InputTooLong] Input {varname}:{clean_val} too long, resetting.')
            clean_val = ''
        CONF_DICT[varname] = clean_val
        current_app.logger.debug(f'[UpdateConfigure] Input {varname}:{CONF_DICT[varname]} updated.')


    conf_mesg = lambda d: f'''Configurations\n
1L:{d.get('moduleID1L', ''):16s} 1C:{d.get('moduleID1C', ''):16s} 1R:{d.get('moduleID1R', ''):16s}\n
2L:{d.get('moduleID2L', ''):16s} 2C:{d.get('moduleID2C', ''):16s} 2R:{d.get('moduleID2R', ''):16s}\n
3L:{d.get('moduleID3L', ''):16s} 3C:{d.get('moduleID3C', ''):16s} 3R:{d.get('moduleID3R', ''):16s}\n
4L:{d.get('moduleID4L', ''):16s} 4C:{d.get('moduleID4C', ''):16s} 4R:{d.get('moduleID4R', ''):16s}\n
5L:{d.get('moduleID5L', ''):16s} 5C:{d.get('moduleID5C', ''):16s} 5R:{d.get('moduleID5R', ''):16s}\n
6L:{d.get('moduleID6L', ''):16s} 6C:{d.get('moduleID6C', ''):16s} 6R:{d.get('moduleID6R', ''):16s}\n
7L:{d.get('moduleID7L', ''):16s} 7C:{d.get('moduleID7C', ''):16s} 7R:{d.get('moduleID7R', ''):16s}\n
8L:{d.get('moduleID8L', ''):16s} 8C:{d.get('moduleID8C', ''):16s} 8R:{d.get('moduleID8R', ''):16s}\n
Note: Configuration saved. Please verify the settings.
    '''


    is_empty_dict = sum( 1  if v else 0 for _,v in CONF_DICT.items()) == 0
    if is_empty_dict:
        errors = 'Got empty configurations!'
        current_app.logger.warning(f'[Configure] {errors}')
        return jsonify({'status': 'error', 'errors': errors}), 400

    current_app.logger.info(conf_mesg(CONF_DICT))
    current_app.logger.info(f'[Configure] Current CONF_DICT: {CONF_DICT}')

    set_server_status('configured')
    # Return JSON with message, status 200 so client JS can alert
    return jsonify({'status': 'success', 'message': conf_mesg(CONF_DICT).replace('  ','__')}), 200




@app.route('/run', methods=['POST'])
def Run():
    ''' run bash command `make run` at background '''
    CMD_ID = 'Run'
    current_app.logger.debug(f'[ServerAction][{CMD_ID}] Got an {CMD_ID} command')
    if not check_jobmode(): return '', 204
    current_app.logger.debug(f'[ServerAction][{CMD_ID}] Got an {CMD_ID} command executing')

    job_stop_flags[CMD_ID].clear()
    if isCommandRunable(shared_state.server_status,CMD_ID):
        set_server_status('running')
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] the server status is idle, activate {CMD_ID} command')

        def background_worker():
            try:
                command = ExecCMD(CMD_ID, CONF_DICT)
                #current_app.logger.debug(f'[bkg CMD Run] {command}')
                run_command(command, CMD_ID)
            finally:
                set_server_status('idle')
                logger.info("Job status set to idle.")
            logger.info('background worker ended')


        t = threading.Thread(target=background_worker)
        t.start()
        set_thread(CMD_ID, t)
    else:
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] Current status is {shared_state.server_status}. reject "{CMD_ID}" command')

    return '', 204


@app.route('/autotest', methods=['POST'])
def AutoTest():
    ''' run formal full-batch automation from the current web configuration '''
    CMD_ID = 'AutoTest'
    current_app.logger.debug(f'[ServerAction][{CMD_ID}] Got an {CMD_ID} command')
    if not check_jobmode(): return '', 204

    ok, errors = save_config_from_json(request.get_json(), require_run_fields=False)
    if not ok:
        current_app.logger.warning(f'[AutoTest] Validation errors: {errors}')
        return jsonify({'status': 'error', 'errors': errors}), 400
    current_app.logger.info(f'[AutoTest] Current CONF_DICT: {CONF_DICT}')

    job_stop_flags[CMD_ID].clear()
    if shared_state.server_status in ['startup', 'initialized', 'configured', 'idle', 'stopped', 'destroyed']:
        populated_modules = {k: v for k, v in module_ids_from_conf(CONF_DICT).items() if v}
        if not populated_modules:
            return jsonify({'status': 'error', 'errors': 'No module IDs configured for AutoTest.'}), 400

        set_server_status('running')
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] activate AutoTest command')

        def background_worker():
            try:
                config_path = build_autotest_config(CONF_DICT)
                status_path = os.path.join('tmp_files', 'runtime', 'current_batch_status.json')
                command = (
                    f'{sys.executable} scripts/run_full_mmts_batch.py '
                    f'-c {config_path} --status-file {status_path}'
                )
                run_command(command, CMD_ID)
            finally:
                set_server_status('idle')
                logger.info("AutoTest job status set to idle.")
            logger.info('AutoTest background worker ended')

        t = threading.Thread(target=background_worker)
        t.start()
        set_thread(CMD_ID, t)
    else:
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] Current status is {shared_state.server_status}. reject "{CMD_ID}" command')

    return '', 204


@app.route('/stop', methods=['POST'])
def Stop():
    if not check_jobmode(): return '', 204
    CMD_ID = 'Stop'

    set_server_status('stopping')
    stop_running_jobs(['Run', 'AutoTest'])
    current_app.logger.debug(f'[ServerAction][Stop] set job_stop_flags as True')

    os.system('pkill -f "make -f makefile_task3" 2>/dev/null')
    os.system('pkill -f "scripts/run_full_mmts_batch.py" 2>/dev/null')
    os.system('pkill -f "control_hmi.py" 2>/dev/null')
    join_job_threads(['Run', 'AutoTest'])

    ## after command Run finished, reset the flag
    job_stop_flags['Run'].clear()
    job_stop_flags['AutoTest'].clear()

    def background_worker():
        try:
            command = ExecCMD(CMD_ID, CONF_DICT)
            #current_app.logger.debug(f'[bkg CMD Stop] {command}')
            run_command(command, CMD_ID)
        finally:
            set_server_status('idle')
            logger.info("Job status set to idle.")
        logger.info('background worker ended')

    t = threading.Thread(target=background_worker)
    t.start()
    t.join() # direct run without accept other command

    set_server_status('stopped')
    return '', 204

@app.route('/destroy', methods=['POST'])
def Destroy():
    if not check_jobmode(): return '', 204
    CMD_ID = 'Destroy'

    if isCommandRunable(shared_state.server_status,CMD_ID):
        set_server_status('destroying')
        for name, flag in job_stop_flags.items(): flag.set()
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] set ALL job_stop_flags as True')
        stop_running_jobs(['Init', 'Run', 'AutoTest', 'Stop'])
        os.system('pkill -f "make -f makefile_task3" 2>/dev/null')
        os.system('pkill -f "scripts/run_full_mmts_batch.py" 2>/dev/null')
        os.system('pkill -f "control_hmi.py" 2>/dev/null')

        join_job_threads(['Init', 'Run', 'AutoTest', 'Stop'])

        ## after command Run finished, reset the flag
        for name, flag in job_stop_flags.items(): flag.clear()
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] reset ALL job_stop_flags')

        def background_worker():
            try:
                command = ExecCMD(CMD_ID, CONF_DICT)
                #current_app.logger.debug(f'[bkg CMD Destroy] {command}')
                run_command(command, CMD_ID)
            finally:
                logger.info("Destory ended")

        t = threading.Thread(target=background_worker)
        t.start()
        t.join() # direct run without accept other command

        set_server_status('destroyed')
    else:
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] Current status is {shared_state.server_status}. reject "{CMD_ID}" command')
    return '', 204

### asdf deleted?
@app.route('/status')
def status():
    hasupdate = False
    
    last_modified = os.path.getmtime(dirDAQresult)
    if last_modified != shared_state.DAQresult_current_modified:
        hasupdate = True
        shared_state.DAQresult_current_modified = last_modified
    
    ### if something updated, list all sub directories as list. Or return empty list
    daq_result_dirs = [ subdir for subdir in os.listdir(dirDAQresult) if os.path.isdir(f'{dirDAQresult}/{subdir}') ] if hasupdate else []
    return jsonify({
        'status': shared_state.server_status,
        'jobmode': shared_state.jobmode,
        'DAQres': daq_result_dirs,
        'batchStatus': read_status(base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))),
    })


@app.route('/main.html')
def main():
    daq_result_dirs = [ subdir for subdir in os.listdir(dirDAQresult) if os.path.isdir(f'{dirDAQresult}/{subdir}') ]
    return render_template('index_task3.html', DAQres=daq_result_dirs, currentCONF=CONF_DICT, ccc='', IVCurveOnline_URL=external_URL, IVCurveOnline_height=external_URL_height,)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='[basicCONFIG] %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app_main = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
        static_url_path='/static',
    )
    app_main.register_blueprint(app, url_prefix='/task3')
    app_main.config["SECRET_KEY"] = '7eCZ^6nUxb6hjN5EbLYak&fvt'
    csrf = CSRFProtect(app_main)


    @app_main.route("/")
    def index():
        return main()
    app_main.run(debug=True, port=5005)
