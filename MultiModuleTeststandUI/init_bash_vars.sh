#!/usr/bin/env sh

THIS_SCRIPT="${BASH_SOURCE[0]}"

CURRENT_PATH=`dirname $( realpath $THIS_SCRIPT ) `

export PYTHONPATH=$PWD:$PYTHONPATH
export LOG_LEVEL=INFO ## DEBUG, INFO, WARNING, CRITICAL

export BASH_SCRIPT_FOLDER=$PWD/scripts/task2_pedestalrun/
export FLASK_BASE=$CURRENT_PATH


export LOG_LEVEL=INFO

######### loading libraries from Andrew's UI
export AndrewModuleTestingGUI_BASE=$PWD/external_packages/hgcal-module-testing-gui
