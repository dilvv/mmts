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
- `PLC_toolkits_mqtt_NTU/control_hmi.py`: HMI thermal-cycle control.
- `PLC_toolkits_mqtt_NTU/plc_io.py`: PLC read/write helpers and status-code logic.

## Dependency Notes

- `pymeasure` is pinned to `0.14.0` because newer PyMeasure releases changed the Keithley 2400 implementation.
- Python code imports `snap7`; the pip package name is `python-snap7`, currently constrained as `python-snap7<3`.

For the detailed UI operation guide, see:

```text
MultiModuleTeststandUI/README.md
```
