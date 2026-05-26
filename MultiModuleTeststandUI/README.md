# MultiModuleTeststandUI

This directory contains the Flask web UI, IV scan controls, DAQ summary views, and full-batch automation entry points for MMTS.

Most day-to-day commands should be run from this directory:

```bash
cd MultiModuleTeststandUI
```

The scripts use relative paths such as `data/`, `scripts/`, `makefile_task3`, and `tmp_files/runtime/`, so running them from another directory can break path resolution.

## Quick Start

Create the virtual environment:

```bash
make -f makefile_initialize_this_GUI flaskb_make_virtual_environment
```

Start the web UI:

```bash
source .venv/bin/activate
source ./init_bash_vars.sh
python3 app.py
```

Open:

```text
http://127.0.0.1:5001
```

Notes:

- PyMeasure is pinned to `0.14.0` because newer PyMeasure releases changed the Keithley 2400 implementation.
- Snap7 is installed through `python-snap7<3` because the code imports `snap7`, while the PyPI package is named `python-snap7`.

## Main Web Workflow

For IV scan / task3:

1. Open the web UI.
2. Select task3 / IV scan.
3. Scan or type module IDs into the module position fields.
4. Select temperature and humidity.
5. For manual IV, click `Initialize`, `Configure`, then `Run`.
6. For full-batch automation, click `AutoTest`.

Button behavior:

- `Run`: runs one manual IV scan through `makefile_task3`.
- `AutoTest`: starts the formal full-batch automation using the current web form module IDs.
- `Stop`: stops the current running task where supported.
- `Destroy`: resets the task state and hardware state.

## Manual IV Scan

The manual IV scan path is:

```text
web task3 page
-> flask_apps/app_task3.py
-> make -f makefile_task3 run
-> scripts/IVscan.run.sh
```

Equivalent shell commands:

```bash
make -f makefile_task3 initialize
make -f makefile_task3 run \
  currentTEMPERATURE=23 \
  currentHUMIDITY=50 \
  moduleID3L=320MLF3WCIH0293
make -f makefile_task3 stop
```

IV scan is intentionally single-threaded. Do not run it with `make -j`.

Manual `Run` uses the temperature and humidity selected on the web page.

## AutoTest From The Web UI

`AutoTest` is the web-triggered formal full-batch workflow.

When you click `AutoTest`, the UI does this:

1. Validates and saves the current web form.
2. Saves scanned module IDs into Flask memory.
3. Generates:

```text
tmp_files/runtime/full_batch_web.yml
```

4. Starts:

```bash
python scripts/run_full_mmts_batch.py \
  -c tmp_files/runtime/full_batch_web.yml \
  --status-file tmp_files/runtime/current_batch_status.json
```

5. Displays progress in the `Auto Batch Status` panel.

In other words, `AutoTest` includes the web configuration step. After the form is saved, it is equivalent to running this command from `MultiModuleTeststandUI`:

```bash
python scripts/run_full_mmts_batch.py \
  -c tmp_files/runtime/full_batch_web.yml \
  --status-file tmp_files/runtime/current_batch_status.json
```

`tmp_files/runtime/full_batch_web.yml` stays on disk until it is overwritten or deleted. Restarting `app.py` does not delete it, but the web form state in memory is cleared after restart.

The formal runner also runs IV initialization internally before each IV scan:

```bash
make -f makefile_task3 initialize
```

`AutoTest` does not use the web page temperature or humidity controls. It uses the formal batch IV settings from `data/full_batch_config.example.yml`.

## Demo Full-Batch Automation

The demo runner is:

```text
scripts/run_full_mmts_batch_demo.py
```

The default demo config is:

```text
data/full_batch_demo.example.yml
```

Run manually from this directory:

```bash
python scripts/run_full_mmts_batch_demo.py \
  -c data/full_batch_demo.example.yml \
  --status-file tmp_files/runtime/current_batch_status.json
```

The demo config keeps the important parameters in one file:

- `demo_controls.dewpoint_threshold_C`
- `demo_controls.dry_run`
- `demo_controls.force_run`
- `cycle_configs.first_cycle.temp_high`
- `cycle_configs.first_cycle.temp_low`
- `cycle_configs.first_cycle.cycles`
- `cycle_configs.first_cycle.idle_warm_min`
- `cycle_configs.first_cycle.idle_cold_min`
- `cycle_configs.remaining_cycles.*`
- `iv_scans.iv1`, `iv_scans.iv2`, `iv_scans.iv3`
- `module_ids`

The demo runner creates temporary HMI YAML files under `tmp_files/runtime/`, then calls `control_hmi.py` from `../PLC_toolkits_mqtt_NTU` by setting the subprocess working directory internally.

## Formal Full-Batch Automation

The formal runner is:

```text
scripts/run_full_mmts_batch.py
```

The example formal config is:

```text
data/full_batch_config.example.yml
```

Current practical note:

- `AutoTest` uses the formal runner.
- The generated `tmp_files/runtime/full_batch_web.yml` is based on `data/full_batch_config.example.yml`.
- The web form replaces the top-level `module_ids` block before starting the formal runner.

## Batch Status Display

The web page reads:

```text
tmp_files/runtime/current_batch_status.json
```

That file is written by the batch runner and shown in the `Auto Batch Status` panel.

Useful fields:

- `status`
- `phase`
- `phase_state`
- `phase_summary`
- `plc.plc_status_text`
- `plc.min_dewpoint_C`
- `updated_at`
- `error_message`

## PLC And Thermal Cycle Status

PLC status code mapping comes from `../PLC_toolkits_mqtt_NTU/plc_io.py`:

```text
0 = door open
1 = standby
2 = countdown warming
3 = warming up
4 = countdown cooling
5 = cooling down
```

The batch sequence currently waits for:

```text
standby -> dewpoint ready -> IV1 -> cooling -> cooling countdown -> IV2 -> standby -> remaining cycles -> standby -> IV3
```

Warming parameters are still configured through `temp_high` and `idle_warm_min`; the runner does not currently use `code 3` as a separate checkpoint.

## Important Files

- `app.py`: main Flask web entry point.
- `flask_apps/app_task3.py`: IV scan page backend and AutoTest route.
- `templates/index_task3.html`: IV scan page and button UI.
- `makefile_task3`: manual IV scan make targets.
- `scripts/run_full_mmts_batch_demo.py`: demo full-batch automation.
- `scripts/run_full_mmts_batch.py`: formal full-batch automation.
- `data/full_batch_demo.example.yml`: demo batch config.
- `data/full_batch_config.example.yml`: formal batch config example.
- `data/mmts_configurations.yaml`: MMTS hardware and external URL config.

## Initialization Targets

Show available initialization targets:

```bash
make -f makefile_initialize_this_GUI help
```

Common setup targets:

```bash
make -f makefile_initialize_this_GUI task1a_setup_andrewGUI
make -f makefile_initialize_this_GUI task3a_clone_IVscan_codes
make -f makefile_initialize_this_GUI task3b_create_mmts_configuration
make -f makefile_initialize_this_GUI flaskb_make_virtual_environment
```

After generating `data/mmts_configurations.yaml`, review it before running hardware operations.
