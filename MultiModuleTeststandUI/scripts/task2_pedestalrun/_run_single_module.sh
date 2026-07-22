#!/bin/bash
LINUXorMAC=LINUX
jobNAME=${1:-testjob}
pullerPORT=${2:-6001}
kriaIP=${3:-192.168.50.153}
hexaboardID=${4:-320XHF4CPM00160}
monitorTIMEOUT=${5:-10}

##### 192.168.50.153
##### 320XHF4CPM00160
##### 6002

##### 192.168.50.152
##### 320XHT4CPM00019
##### 6003


tmpPIDlist=tmp_PIDlist${jobNAME}_run.txt
touch $tmpPIDlist
/bin/rm $tmpPIDlist
touch $tmpPIDlist

# This lets your script react properly if it receives SIGINT.
# Function to cleanup on SIGINT or exit
cleanup() {
	echo "Caught SIGINT or exit, cleaning up..."
	if [ -f "$tmpPIDlist" ]; then
		while read -r pid; do
			if kill -0 "$pid" 2>/dev/null; then
				echo "Killing PID $pid"
				kill -TERM -"$pid" 2>/dev/null
			fi
			sleep 0.5
		done <"$tmpPIDlist"
		/bin/rm -f "$tmpPIDlist"
    echo "[${jobNAME} - StatusChangeError] Job terminated";
	fi
	exit 1
}

# Trap SIGINT (Ctrl+C), SIGTERM, and script exit
trap cleanup SIGINT SIGTERM EXIT

#### conf1 : run daq client at background
env_cmd_running_at_background__check_timeout() {
	sh step2a.kria_env_setup.sh $kriaIP
	sleep 0.5
	sh step3a.daqclient.sh $pullerPORT
}
#### conf2 : mainjob
mainjob_force_terminated_if_envcmd_timeout() {
	sh step4a.takedata.sh $jobNAME $kriaIP $hexaboardID $pullerPORT
}

# Log file for the first command output
FIRST_LOG="log_${jobNAME}_daqclient.txt"
# Log file for the second command output
SECOND_LOG="log_${jobNAME}_takedata.txt"

echo "[$jobNAME - StatusChangeRunning] start code aa.sh"

# Start the first command in the background and redirect output to FIRST_LOG
# Replace 'env_cmd_running_at_background__check_timeout' with the actual command you want to run
#env_cmd_running_at_background__check_timeout 2>&1  | tee "$FIRST_LOG" &
#setsid bash -c 'env_cmd_running_at_background__check_timeout 2>&1  | tee "$0"' "$FIRST_LOG" &

# Start a command in a new process group via subshell
(
	# Make subshell ignore SIGINT and create a new process group
	trap '' INT
	env_cmd_running_at_background__check_timeout 2>&1 | tee "$FIRST_LOG"
) &
CMD_PID1=$!
# Capture the PID of the background command
# Get its process group ID (PGID)
FIRST_CMD_PID=$(ps -o pgid= -p "$CMD_PID1" | tr -d ' ')
echo $FIRST_CMD_PID >>$tmpPIDlist

# Wait for 5 seconds
sleep 8

# Start the second command and redirect output to SECOND_LOG
# Start a command in a new process group via subshell
(
	# Make subshell ignore SIGINT and create a new process group
	trap '' INT
	mainjob_force_terminated_if_envcmd_timeout 2>&1 | tee "$SECOND_LOG"
) &
CMD_PID2=$!

# Store the PID of the second command
SECOND_CMD_PID=$(ps -o pgid= -p "$CMD_PID2" | tr -d ' ')
echo $SECOND_CMD_PID >>$tmpPIDlist

# Function to monitor the first command output and set a timeout
kill_process_if_timeout_happened() {
	timeoutFORkill="$1"
	checkLOGfile="$2"
	shift 2
	commandPIDs=("$@") # Remaining arguments are PIDs

	echo "Monitoring output of the first command..." >>"$checkLOGfile"

	LAST_OUTPUT_TIME=$(date +%s)
	if [ "$LINUXorMAC" == "LINUX" ]; then statOPT="-c %s"; fi
	if [ "$LINUXorMAC" == "MAC" ]; then statOPT="-f %z"; fi

	timeout_happened=0
	while kill -0 "${commandPIDs[0]}" 2>/dev/null; do
		sleep 1
		CURRENT_SIZE=$(stat $statOPT "$checkLOGfile")
		sleep 1
		NEW_SIZE=$(stat $statOPT "$checkLOGfile")

		if [[ "$CURRENT_SIZE" -eq "$NEW_SIZE" ]]; then
			CURRENT_TIME=$(date +%s)
			if ((CURRENT_TIME - LAST_OUTPUT_TIME > timeoutFORkill)); then
				timeout_happened=1
				break
			fi
		else
			LAST_OUTPUT_TIME=$(date +%s)
		fi
	done

	if [ "$timeout_happened" == 1 ]; then
		echo "No output for $timeoutFORkill seconds, terminating processes..." >>"$checkLOGfile"
		echo "No output for $timeoutFORkill seconds, terminating processes..."
		for pid in "${commandPIDs[@]}"; do
			echo "Killing PID $pid"
			kill -TERM -"$pid" 2>/dev/null
		done
	fi
	echo "kill_process_if_timeout_happened finished!"
}

# Start the output checker in the background
kill_process_if_timeout_happened $monitorTIMEOUT $FIRST_LOG $FIRST_CMD_PID $SECOND_CMD_PID &

# Store the output checker PID
OUTPUT_CHECK_PID=$!
echo $OUTPUT_CHECK_PID >>$tmpPIDlist

# Wait for the second command to finish. Second command might correctly finished or timeout killed.
wait $CMD_PID2

trap - SIGINT SIGTERM EXIT

# If second command finished but OUTPUT_CHECK_PID is still running, it means code correctly finished.
# kill -0 PID --> result: 0 -> still running
# kill -0 PID --> result: 1 -> no such process
if kill -0 "${OUTPUT_CHECK_PID}" 2>/dev/null; then
	# Once the second command is finished, terminate the output checker
	kill $OUTPUT_CHECK_PID

	# If the first command is still running, terminate it and log the action
	echo "[$jobNAME - StatusChangeIdle] FINISHED"
	if kill -0 $FIRST_CMD_PID 2>/dev/null; then
		echo "Terminating the first command..." >>"$FIRST_LOG"
		kill -TERM -$FIRST_CMD_PID
	fi
else
	echo "[$jobNAME - StatusChangeError] timeout happened!!! exit code"
fi

/bin/rm $tmpPIDlist
echo FINISHED!!
