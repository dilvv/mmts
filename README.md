# MMTS

[中文说明](./README.zh-CN.md)

This repository contains the MMTS control and monitoring software.

There are two main directories:

- `PLC_toolkits_mqtt_NTU`
  PLC, chiller, HMI control, environment monitoring, MQTT, and database tools.
- `MultiModuleTeststandUI`
  Flask web UI, manual IV scan controls, DAQ summary pages, and batch automation scripts.

For most day-to-day MMTS operations, work from:

```bash
cd MultiModuleTeststandUI
```

Many scripts use relative paths such as `data/`, `scripts/`, `makefile_task3`, and `tmp_files/runtime/`.

## Quick Start

```bash
cd MultiModuleTeststandUI
source .venv/bin/activate
source ./init_bash_vars.sh
python3 app.py
```

Open:

```text
http://127.0.0.1:5001
```

## Main Web Workflows

Manual IV scan from the task3 page:

```text
Initialize -> scan module IDs -> Configure -> Run
```

`Run` starts one IV scan through:

```bash
make -f makefile_task3 run
```

Manual `Run` uses the temperature and humidity selected on the web page.

### Manual segmented Thermal Cycle

The task3 `Thermal Cycle` workflow is separate from `AutoTest`. Enter the total
number of logical cycles in `Cycles` and, optionally, a comma-separated list of
1-based cycle numbers in `IV2 cycles`, for example `2,12,22`.

The sequence is:

```text
initial IV1
-> wait for both dewpoints to pass the configured threshold
-> execute planned PLC thermal segments
-> run IV2 during every selected cycle
-> wait for stable PLC Standby after every segment
-> final IV3
```

The segment planner reduces PLC configuration and START traffic:

- Consecutive cycles that do not contain IV2 form one normal segment with
  `cycles=N` and `idle_cold_min=10`.
- Every selected IV2 cycle is a separate one-cycle segment with `cycles=1` and
  `idle_cold_min=59`. Adjacent IV2 cycles are not merged.
- Each segment normally needs one complete `control_hmi.py` invocation. The
  runner validates that the PLC accepted START and permits at most one second
  complete invocation if the first one fails validation.

For example, 92 logical cycles with IV2 on
`2,12,22,32,42,52,62,72,82,92` produce 20 segments and therefore normally 20
complete PLC configuration/START invocations, instead of one invocation for
every logical cycle. The internal retry behavior of `control_hmi.py` is
unchanged, so this count is not the same as low-level START-bit attempts.

Runtime PLC YAML files are generated under `MultiModuleTeststandUI/tmp_files/runtime/`.
`PLC_toolkits_mqtt_NTU/HMI_Control_single_cycle.yml` is used only as an
immutable template.

The `Auto Batch Status` panel shows the batch, segment number, global cycle
range, completed logical cycles, elapsed time, selected/next IV2 cycle, PLC
state, dewpoints, and any error. Browser refreshes or reopening the page do not
stop the workflow; the `app.py` process and the runner must remain alive.

Use the dedicated `Stop Thermal/AutoTest` button to stop this workflow. The
historical `Stop` button remains IV-only. A workflow failure does not
automatically issue PLC STOP, so operators must inspect the PLC state and use
the dedicated stop deliberately when required.

For a long-running batch, do not stop/restart `app.py`, run another workflow,
or perform source-changing Git operations such as pull, checkout, rebase, or
merge. A commit or push that does not modify checked-out source files is safe,
but should still be followed by verifying that the same app and runner PIDs
remain active.

Web-triggered formal batch automation:

```text
scan module IDs -> AutoTest
```

`AutoTest` validates and saves the current web form into:

```text
MultiModuleTeststandUI/tmp_files/runtime/full_batch_web.yml
```

Then it starts:

```bash
python scripts/run_full_mmts_batch.py \
  -c tmp_files/runtime/full_batch_web.yml \
  --status-file tmp_files/runtime/current_batch_status.json
```

So `AutoTest` includes the web configuration step and is equivalent to running the command above from inside `MultiModuleTeststandUI` after the form has been saved. The formal runner also calls `make -f makefile_task3 initialize` before each IV scan.

`AutoTest` does not use the web page temperature or humidity controls. It uses the formal batch IV settings from `data/full_batch_config.example.yml`.

`IV3 Test` is a manual shortcut next to `AutoTest` for the final retest case. It saves the current web form module IDs, reads the formal `iv_scans.iv3` values, and is equivalent to:

```bash
make -f makefile_task3 initialize && make -f makefile_task3 run \
  moduleID... \
  currentTEMPERATURE=20 \
  currentHUMIDITY=0 \
  maxVOLTAGE=850
```

The exact temperature, humidity, and voltage values come from `data/full_batch_config.example.yml`.

If IV initialization fails because the VITREK or Keithley RS232 devices are not connected, AutoTest automatically runs:

```bash
make -f makefile_task3 destroy
```

and moves the web server state to `destroyed`.

The task3 page reads `tmp_files/runtime/current_batch_status.json` and displays progress in the `Auto Batch Status` panel.

## Automation Scripts

Demo runner:

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`
- `MultiModuleTeststandUI/data/full_batch_demo.example.yml`

Formal runner:

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- `MultiModuleTeststandUI/data/full_batch_config.example.yml`

`AutoTest` uses the formal runner. The web page generates `tmp_files/runtime/full_batch_web.yml` from `data/full_batch_config.example.yml` and replaces the `module_ids` block with the IDs scanned in the browser.

## Batch Sequence

The intended full-batch sequence is:

```text
precheck
-> IV1
-> wait for dewpoint
-> first thermal cycle
-> wait for cooling down
-> wait for cooling countdown
-> IV2
-> wait for standby
-> remaining 5 thermal cycles
-> wait for standby
-> IV3
```

PLC status codes are computed in `PLC_toolkits_mqtt_NTU/plc_io.py`:

```text
0 = door open
1 = standby
2 = countdown warming
3 = warming up
4 = countdown cooling
5 = cooling down
```

## Important Entry Points

- `MultiModuleTeststandUI/app.py`: main Flask web app.
- `MultiModuleTeststandUI/flask_apps/app_task3.py`: task3 backend, manual IV, and AutoTest route.
- `MultiModuleTeststandUI/templates/index_task3.html`: task3 page UI.
- `MultiModuleTeststandUI/makefile_task3`: manual IV scan make targets.
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`: demo batch automation.
- `MultiModuleTeststandUI/scripts/run_selected_iv2_thermal_cycles.py`: segmented manual Thermal Cycle runner.
- `PLC_toolkits_mqtt_NTU/control_hmi.py`: HMI thermal-cycle control.
- `PLC_toolkits_mqtt_NTU/plc_io.py`: PLC read/write helpers and status-code logic.

## Dependency Notes

- `pymeasure` is pinned to `0.14.0` because newer PyMeasure releases changed the Keithley 2400 implementation.
- Python code imports `snap7`; the pip package name is `python-snap7`, currently constrained as `python-snap7<3`.

For the detailed UI operation guide, see:

```text
MultiModuleTeststandUI/README.md
```

## Sync MultiModuleTeststandUI from upstream

The upstream UI repository is registered as:

```text
upstream-ui = git@github.com:ltsai323/MultiModuleTeststandUI.git
```

The commands below update only the `MultiModuleTeststandUI/` subtree. They do
not modify `PLC_toolkits_mqtt_NTU/`.

Run them from the root of this `mmts` repository with a clean working tree:

```bash
cd mmts

git switch main
git pull --ff-only origin main
git fetch upstream-ui

git switch -c sync-upstream-ui
git subtree pull \
  --prefix=MultiModuleTeststandUI \
  upstream-ui main \
  --squash
```

Command explanation:

- `cd mmts`: enter the root repository containing both
  `MultiModuleTeststandUI/` and `PLC_toolkits_mqtt_NTU/`.
- `git switch main`: switch to the local `main` branch.
- `git pull --ff-only origin main`: update local `main` from
  `dilvv/mmts`. It stops instead of creating an unexpected merge commit if the
  branches have diverged.
- `git fetch upstream-ui`: download the latest history from
  `ltsai323/MultiModuleTeststandUI` without changing local files.
- `git switch -c sync-upstream-ui`: create a temporary integration branch so
  an upstream update does not immediately change local `main`.
- `git subtree pull --prefix=MultiModuleTeststandUI upstream-ui main --squash`:
  merge the upstream repository's `main` branch into the local
  `MultiModuleTeststandUI/` directory. `--squash` records one synchronization
  commit in this repository.

If the synchronization succeeds, test the GUI before merging it into this
repository's `main`:

```bash
git switch main
git merge --ff-only sync-upstream-ui
git push origin main
git branch -d sync-upstream-ui
```

If both repositories changed different lines, Git normally merges them
automatically. If both changed the same lines, Git stops with a conflict and
requires a manual decision; it does not silently overwrite the local changes.

`git subtree` must be installed on the machine running these commands. Some
Git for Windows installations do not bundle it; the Linux test machine should
install the `git-subtree` package if the command is unavailable.
