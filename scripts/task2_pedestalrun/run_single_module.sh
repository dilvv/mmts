#!/bin/bash
pullerPORT=${1:-6001}
kriaIP=${2:-192.168.50.153}
hexaboardID=${3:-320XHF4CPM00160}
monitorTIMEOUT=${4:-20}
logTAG=${5:-testlog}

tmpPIDlist="tmp_PIDlist_${logTAG}_run.txt"
FIRST_LOG="logs/log_${logTAG}_daqclient.txt"
SECOND_LOG="logs/log_${logTAG}_takedata.txt"
ALL_LOG="logs/log_${logTAG}_alllogs.txt"




# Example of daq-client running at background but a timeout set
# The timeout uses "timeout" command in bash, which kills jobs in 10 seconds
# So the job will be killed if the daq-client stopped working.
function daq_client_with_timeout() {
    kria_ip=$1
    puller_port=$2
    echo "----------- daq_client_with_timeout() got kriaIP $kria_ip and port $puller_port ==-==="
    sh $BASH_SCRIPT_FOLDER/step2a.kria_env_setup.sh $kria_ip
    sleep 0.5
    sh $BASH_SCRIPT_FOLDER/step3a.daqclient.sh $puller_port
    echo "FINISHED" ## to identify this command executed correctly
}

# Example main job function
function mainjob() {
    sleep 7
    sh $BASH_SCRIPT_FOLDER/step4a.takedata.sh  $kriaIP $hexaboardID $pullerPORT
    echo "FINISHED" ## to identify this command executed correctly
}


























# Cleanup function
function cleanup() {
    echo "Caught SIGINT or exit, cleaning up..."
    [ ! -f $tmpPIDlist ] && return

    SELF_PGID=$(ps -o pgid= -p $$ | tr -d ' ')

    if [ -f "$tmpPIDlist" ]; then
        tac "$tmpPIDlist" | while read -r pid; do # read line by line but in reversed
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null
            fi
        done
        /bin/rm -f "$tmpPIDlist"
        echo "[${hexaboardID} - StatusChangeError] Job terminated"
    fi
#    echo 'b@[cleanup] return 0'
    exit 0
}



function mainfunc() {
# Create a fresh PID list file
: > "$tmpPIDlist"

# Trap in the main script only
trap cleanup SIGINT SIGTERM EXIT
export -f daq_client_with_timeout
echo timeout ${monitorTIMEOUT}s bash -c "daq_client_with_timeout $kriaIP $pullerPORT"
timeout ${monitorTIMEOUT}s bash -c "daq_client_with_timeout $kriaIP $pullerPORT" 2>&1 | tee $FIRST_LOG &
#timeout 15s bash -c daq_client_with_timeout &
CMD_PID1=$!
echo $CMD_PID1 >> $tmpPIDlist
sleep 1

mainjob 2>&1 | tee $SECOND_LOG &
CMD_PID2=$!
echo $CMD_PID2 >> $tmpPIDlist

# waiting for job finished. There are 2 situations:
# 1. mainjob finished: normal situation
# 2. env job finished: which is timeout happened. This is failed situation
wait -n
function checkCMD() { cmdPID=$1; name=$2; if kill -0 "$cmdPID" 2>/dev/null; then echo "[cmdRunning] $name is still running"; fi; }
if kill -0 "$CMD_PID2" 2>/dev/null; then FAILED_JOB=1; fi
checkCMD $CMD_PID1 daq-client
checkCMD $CMD_PID2 mainjob



# Disable traps since the job completed normally
trap - SIGINT SIGTERM EXIT


echo clean up tmpPIDlist $tmpPIDlist
cat $tmpPIDlist
cleanup # clean up if something ended
/bin/rm -f $tmpPIDlist

echo "FINISHED!!"
exit 0
}

## end of function definitions




mainfunc 2>&1 | tee $ALL_LOG
echo mainfunc finished
