#!/usr/bin/env sh
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh

exec_at_kria 'kconn_pwr on'

### output message is
<<LISTED_OUTPUT_MESG
" SUC
Turning on payload power
"
LISTED_OUTPUT_MESG
