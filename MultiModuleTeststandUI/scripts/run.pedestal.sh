moduleID="'$1'"
runTAG="'$2'"
mmtsPOSITION="'$3'"
moduleSTATUS="'$4'"
daqINSPECTOR="'$5'"

mmtsCONF=${FLASK_BASE}/data/mmts_configurations.yaml
function the_exit() { echo "the_exit - "$1; exit 0; } ## return 0 prevent make command failed


[ "$AndrewModuleTestingGUI_BASE" == "" ] && echo "[InvalidPath] Need to 'source init_bash_bars.sh' before use" && exit 1

cd $AndrewModuleTestingGUI_BASE
echo [BASHCMD] python3 InteractionGUI.CLI.py $mmtsCONF $moduleID $runTAG $mmtsPOSITION $moduleSTATUS $daqINSPECTOR
python3 InteractionGUI.CLI.py $mmtsCONF $moduleID $runTAG $mmtsPOSITION $moduleSTATUS $daqINSPECTOR \
  || the_exit "[Error] InteractionGUI.CLI.py got error.  abort... "

#python3 InteractionGUI.CLI.py "'${FLASK_BASE}/data/mmts_configurations.yaml'" '320-XH-T4C-PM-00019' 'run1' '1L' 'Untaped' 'test-user' || exit 0
cd -
