# MMTS

[中文说明](./README.zh-CN.md)

This repository contains two main parts:

- `PLC_toolkits_mqtt_NTU`
  The PLC, chiller, telemetry, MQTT, and database side.
- `MultiModuleTeststandUI`
  The Flask web UI, IV scan controls, DAQ summary pages, and batch automation scripts.

## What Is In This Repo

Current workflow pieces:

- manual IV scan from the web UI
- PLC-driven thermal-cycle control
- environment monitoring through `plc_to_db.py`
- demo full-batch automation for workflow validation
- formal full-batch automation for the full 3-IV + 6-cycle sequence

Important entry points:

- `PLC_toolkits_mqtt_NTU/plc_to_db.py`
- `PLC_toolkits_mqtt_NTU/control_hmi.py`
- `MultiModuleTeststandUI/app.py`
- `MultiModuleTeststandUI/flask_apps/app_task3.py`
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`

## Manual Flow

The original manual flow is still available.

1. Keep `PLC_toolkits_mqtt_NTU/plc_to_db.py` running.
2. Start `MultiModuleTeststandUI/app.py`.
3. Open the IV page and use `Initialize -> Configure -> Run`.
4. Start the first cycle manually with `control_hmi.py`.
5. Start the remaining 5 cycles manually with `control_hmi.py -c HMI_Control_5cycle.yml`.
6. Watch PLC status, dewpoint, and IV curves from the UI / Grafana.

The manual IV path still goes through:

- `MultiModuleTeststandUI/flask_apps/app_task3.py`
- `MultiModuleTeststandUI/makefile_task3`
- `MultiModuleTeststandUI/scripts/IVscan.initialize.sh`
- `MultiModuleTeststandUI/scripts/IVscan.run.sh`

## Demo Automation

The demo runner is separate from the formal runner. It is intended to validate that the automation sequence can run through with adjustable parameters before using the full production settings.

Files:

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`
- `MultiModuleTeststandUI/data/full_batch_demo.example.yml`
- `MultiModuleTeststandUI/docs/demo_batch.md`

The demo runner keeps the same dewpoint acquisition method:

- read PLC offset `314` for `DMT-01`
- read PLC offset `356` for `DMT-02`
- convert with `1.25 * raw - 5`

The demo dewpoint gate uses the original simplified rule:

- compare `min(DMT-01, DMT-02)` against the configured threshold

Demo settings you can change:

- `demo_controls.dewpoint_threshold_C`
- `cycle_configs.first_cycle.temp_low`
- `cycle_configs.remaining_cycles.temp_low`
- `cycle_configs.remaining_cycles.idle_warm_min`
- `cycle_configs.remaining_cycles.idle_cold_min`
- `demo_controls.dry_run`
- `demo_controls.force_run`

Recommended first test:

```bash
python MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py -c MultiModuleTeststandUI/data/full_batch_demo.example.yml
```

Suggested demo approach:

1. Fill one or more `module_ids`.
2. Keep `dry_run: true`.
3. Reduce low temperature and hold times.
4. Confirm the phase transitions and batch status updates.
5. Only then switch to real PLC execution.

## Formal Full-Batch Automation

The formal runner is:

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- `MultiModuleTeststandUI/data/full_batch_config.example.yml`

It is intended to execute:

1. IV1 at room temperature / humidity 50
2. First thermal cycle
3. IV2 during the first low-temperature countdown stage
4. Remaining 5 cycles
5. IV3 after the last cycle

The runner writes shared progress information to:

- `MultiModuleTeststandUI/tmp_files/runtime/current_batch_status.json`

The task3 page reads that file and shows a read-only `Auto Batch Status` panel, so the UI can stay open for human monitoring while the automation runs in the background.

Recommended formal procedure:

1. Confirm `plc_to_db.py` is running.
2. Confirm the task3 page is reachable.
3. Fill real module IDs into `full_batch_config.example.yml` or a copied config.
4. Verify dewpoint rule, cycle configuration, and timeouts.
5. Start the batch runner from the shell.
6. Keep the UI open for monitoring and manual intervention if needed.

Example:

```bash
python MultiModuleTeststandUI/scripts/run_full_mmts_batch.py -c MultiModuleTeststandUI/data/full_batch_config.example.yml
```

## Windows Local Task3 Startup

If you want to run only `app_task3.py` locally on Windows for page testing, use the project virtual environment and set the required environment variables first:

```powershell
cd C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI
$env:AndrewModuleTestingGUI_BASE='C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI\external_packages\hgcal-module-testing-gui'
$env:PYTHONPATH='C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI'
.\.venv\Scripts\python.exe .\flask_apps\app_task3.py
```

Then open:

- `http://127.0.0.1:5005/`

Notes:

- `app.py` is the full MMTS web UI and normally uses port `5001`.
- `flask_apps/app_task3.py` is the standalone task3 page for local testing and uses port `5005`.

## Notes

- The new automation scripts were added alongside the original manual workflow.
- The demo runner and the formal runner are intentionally separate.
- The UI-specific README remains under `MultiModuleTeststandUI/README.md`.
- A Chinese project-level README is available at `README.zh-CN.md`.
