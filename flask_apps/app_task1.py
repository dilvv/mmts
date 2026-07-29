import subprocess
import threading
import logging
from flask import Flask, render_template, request, jsonify, Blueprint
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms.validators import DataRequired, Regexp, InputRequired
from wtforms import StringField, SubmitField, RadioField
import flask_apps.shared_state as shared_state
from PythonTools.server_status import isCommandRunable
import re
import os
### HTTP status codes https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

JOBMODE = 'task1' # single pedestal run

andrewCONF = f'{os.environ.get("AndrewModuleTestingGUI_BASE")}/configuration.yaml'
dirDAQresult = ''
DEFAULT_INSPECTORS = []
try:
    with open(andrewCONF, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        DEFAULT_INSPECTORS = conf['Inspectors']
        dirDAQresult = f"{conf['DataLoc']}/daqplots/"
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[NoEnvVar] Need to `source ./init_bash_vars.sh` before execute this file') from e

CONF_DICT = {
        'inspector': '',
        'moduleSTATUS': '',
        'moduleID1L': '',
        'moduleID1C': '',
        'moduleID1R': '',

        'moduleID2L': '',
        'moduleID2C': '',
        'moduleID2R': '',

        'moduleID3L': '',
        'moduleID3C': '',
        'moduleID3R': '',
        }

def ExecCMD(jobID:str, confDICT:dict):
    if jobID == 'Init':
        return 'make -f makefile_task1 initialize JobName=Init'
    if jobID == 'Run':
        shared_state.runidx+=1
        runTAG = f'run{shared_state.runidx}'
        dictOPTs = ' '.join([ f'{key}={val}' for key,val in confDICT.items() if val != '' ])
        return f'make -f makefile_task1 run -j6 JobName=Run runTAG={runTAG} ' + dictOPTs
    if jobID == 'Stop':
        return 'make -f makefile_task1 stop JobName=Stop'
    if jobID == 'Destroy':
        return 'make -f makefile_task1 destroy JobName=Destroy'



#logger = logging.getLogger('flask.app')
logger = logging.getLogger('werkzeug')


app = Blueprint('app_task1', __name__)


job_stop_flags = {
        'Init': threading.Event(),
        'Run': threading.Event(),
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
        'Stop': None,
        'Destroy': None,
        }
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

alphanumeric_validator = Regexp("^[a-zA-Z0-9\-]*$", message="Only letters and numbers and dash allowed.")
#alphanumeric_validator = Regexp("^[a-zA-Z0-9]*$", message="Only letters and numbers allowed.")
class ConfigForm(FlaskForm):
    inspector = StringField("inspector", validators=[InputRequired()])
    moduleSTATUS = StringField("moduleSTATUS", validators=[InputRequired()])
   #moduleSTATUS = RadioField("moduleSTATUS", validators=[InputRequired()])
    moduleID1L = StringField("moduleID1L", validators=[alphanumeric_validator])
    moduleID1C = StringField("moduleID1C", validators=[alphanumeric_validator])
    moduleID1R = StringField("moduleID1R", validators=[alphanumeric_validator])

    moduleID2L = StringField("moduleID2L", validators=[alphanumeric_validator])
    moduleID2C = StringField("moduleID2C", validators=[alphanumeric_validator])
    moduleID2R = StringField("moduleID2R", validators=[alphanumeric_validator])

    moduleID3L = StringField("moduleID3L", validators=[alphanumeric_validator])
    moduleID3C = StringField("moduleID3C", validators=[alphanumeric_validator])
    moduleID3R = StringField("moduleID3R", validators=[alphanumeric_validator])
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
        clean_val = ignore_special_characters(value)
        if len(clean_val) > 20:
            current_app.logger.warning(f'[InputTooLong] Input {varname}:{clean_val} too long, resetting.')
            clean_val = ''
        CONF_DICT[varname] = clean_val
        current_app.logger.debug(f'[UpdateConfigure] Input {varname}:{CONF_DICT[varname]} updated.')


    conf_mesg = lambda d: f'''Configurations\n
        1L: {d.get('moduleID1L', ''):12s}\n1C: {d.get('moduleID1C', ''):12s}\n1R: {d.get('moduleID1R', ''):12s}\n
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
    return jsonify({'status': 'success', 'message': conf_mesg(CONF_DICT)}), 200




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


@app.route('/stop', methods=['POST'])
def Stop():
    if not check_jobmode(): return '', 204
    CMD_ID = 'Stop'

    set_server_status('stopping')
    job_stop_flags['Run'].set()
    current_app.logger.debug(f'[ServerAction][Stop] set job_stop_flags as True')

    os.system('pkill make 2>/dev/null') ## force kill all jobs from make commands
    if job_thread['Run'] and job_thread['Run'].is_alive():
        job_thread['Run'].join()

    ## after command Run finished, reset the flag
    job_stop_flags['Run'].clear()

    def background_worker():
        try:
            command = ExecCMD(CMD_ID, CONF_DICT)
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
        os.system('pkill make 2>/dev/null') ## force kill all jobs from make commands

        for name, t in job_thread.items():
            if t and t.is_alive():
                t.join() # waiting for all jobs finished

        ## after command Run finished, reset the flag
        for name, flag in job_stop_flags.items(): flag.clear()
        current_app.logger.debug(f'[ServerAction][{CMD_ID}] reset ALL job_stop_flags')

        def background_worker():
            try:
                command = ExecCMD(CMD_ID, CONF_DICT)
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

@app.route('/status')
def status():
    hasupdate = False
    
    last_modified = os.path.getmtime(dirDAQresult)
    if last_modified != shared_state.DAQresult_current_modified:
        hasupdate = True
        shared_state.DAQresult_current_modified = last_modified
    
    ### if something updated, list all sub directories as list. Or return empty list
    daq_result_dirs = [ subdir for subdir in os.listdir(dirDAQresult) if os.path.isdir(f'{dirDAQresult}/{subdir}') ] if hasupdate else []
    return jsonify( {'status':shared_state.server_status, 'jobmode': shared_state.jobmode, 'DAQres': daq_result_dirs} )


@app.route('/main.html')
def main():
    daq_result_dirs = [ subdir for subdir in os.listdir(dirDAQresult) if os.path.isdir(f'{dirDAQresult}/{subdir}') ]
    return render_template('index_task1.html', DAQres=daq_result_dirs, inspectors=DEFAULT_INSPECTORS)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='[basicCONFIG] %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')
    app_main = Flask(__name__)
    app_main.register_blueprint(app, url_prefix='/task1')
    app_main.config["SECRET_KEY"] = '7eCZ^6nUxb6hjN5EbLYak&fvt'
    csrf = CSRFProtect(app_main)


    @app_main.route("/")
    def index():
        return render_template("index_task1.html")
    app_main.run(debug=True)
