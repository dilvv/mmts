from flask import Flask, render_template, request, jsonify
import flask_apps.shared_state as shared_state
from flask_wtf.csrf import CSRFProtect
import sys

# app.py
import logging
import logging.config
from datetime import datetime
log = logging.getLogger(__name__)

import os
os.system('mkdir -p logs')
logfile = datetime.now().strftime("logs/app_%Y%m%d-%H%M%S.log")

mmtsCONF = 'data/mmts_configurations.yaml'
external_URL = ''
external_URL_height = '200px'
try:
    with open(mmtsCONF, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        external_URL = conf['externalURL']['EnvMonitor']['URL']
        external_URL_height = conf['externalURL']['EnvMonitor']['height']
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[LackOfMMTSconf] Need to create configuration file "data/mmts_configuration.yaml"') from e

class StatusFilter(logging.Filter):
    def filter(self, record):
        # Return False to exclude log records containing "/status HTTP/1.1"
        msg = record.getMessage()
        if "/status HTTP/1.1" in msg:
            return False
        return True

#logging.basicConfig(
#    level=logging.DEBUG,
#    format='[basicCONFIG AAAA] %(levelname)s - %(message)s',
#    datefmt='%H:%M:%S'
#)
#logger = logging.getLogger('flask.app')
#logger = logging.getLogger('werkzeug')
#logger.addFilter(StatusFilter())
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "status_filter": {
            "()": StatusFilter
        }
    },
    "formatters": {
        "default": {
            "format": "[%(levelname)s] %(asctime)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
            "filters": ["status_filter"],
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "level": "DEBUG",
            "filename": logfile,
            "encoding": "utf8",
            "mode": "a"
        }
    },
    "loggers": {
        # Configure your Flask app logger
        "flask.app": {  # Replace with your app's module name or use app.logger.name
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        # Werkzeug logger - optional, also filtered
        "werkzeug": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "filters": ["status_filter"],
            "propagate": False
        }
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console", "file"]
    }
}
logging.config.dictConfig(LOGGING_CONFIG)



import flask_apps.app_task1    as app_task1
import flask_apps.app_task2    as app_task2
import flask_apps.app_task3    as app_task3 #import flask_apps.app_task3_plot    as app_plot3
import flask_apps.app_daqsummary as app_daqsummary

app = Flask(__name__)
app.config["SECRET_KEY"] = '7eCZ^6nUxb6hjN5EbLYak&fvt'
csrf = CSRFProtect(app)
app.register_blueprint(app_task1.app, url_prefix='/task1')
app.register_blueprint(app_task2.app, url_prefix='/task2')
app.register_blueprint(app_task3.app, url_prefix='/task3')
#app.register_blueprint(app_plot3.app)

app.register_blueprint(app_daqsummary.app)


@app.route("/")
def index():
    return render_template("index_mainpage.html", selected_option=shared_state.jobmode, EnvMonitor_URL=external_URL, EnvMonitor_height=external_URL_height)

@app.route("/index.html")
def index_alias():
    return render_template("index_mainpage.html", selected_option=shared_state.jobmode, EnvMonitor_URL=external_URL, EnvMonitor_height=external_URL_height)

@app.route("/set_option", methods=["POST"])
def set_option():
    data = request.get_json()
    ''' data = { 'option': 'task1' } '''
    log.info(f'[set_option] Got option {data} and current server status {shared_state.server_status} and jobmode {shared_state.jobmode}')

    ### got valid loaded json
    if "option" not in data:
        return jsonify({"status": "error", "message": f'[InvalidOption] set_option() received invalid input "{data}".'}), 400

    ### the same jobmode: do nothing
    if shared_state.jobmode == data["option"]:
        return jsonify({'status': 'success', 'message': f'[NoAnyChange] job mode is {data["option"]}'})

    ### change job mode: Only for status is "startup" or "destroyed"
    if shared_state.server_status in ['startup','destroyed']:
        mesg = f'[NewJobMode] set_option() set jobmode as {data["option"]}'
        shared_state.jobmode = data["option"]
        log.info(mesg)
        return jsonify({"status": "success", 'message': mesg})
    ### remain original job mode: ignore request
    else:
        mesg = f'[set_option] ignore changing jobmode due to jobmode {shared_state.jobmode} / status {shared_state.server_status}'
        log.info(mesg)
        return jsonify({"status": "success", "message": mesg})
        

#@app.route('/status')
#def status():
#    return jsonify( {'status':shared_state.server_status, 'jobmode':shared_state.jobmode} )

### note only if jobmode is notSELECTED or job status is DESTROYED, allowed to select new jobmode




if __name__ == "__main__":
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
                        format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
                        datefmt='%H:%M:%S')
    log = logging.getLogger(__name__)
    if DEBUG_MODE:
        shared_state.debug_mode = True
        app.run(debug=True, port=5005, host='0.0.0.0') ### for test product only use http://127.0.0.1:5005 access this port. http://192.168.o.x:5005 cannot access this port
    else:
        shared_state.debug_mode = False
        app.run(debug=True, port=5001, host='0.0.0.0') ### for stable product so you can use http://192.16..o.x:5001 access it

