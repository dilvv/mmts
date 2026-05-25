# MultiModuleTeststandUI

This repository contains the MMTS web UI and the scripts used to run:

- manual IV scan from the web page
- PLC-backed thermal-cycle control
- demo full-batch automation for workflow validation
- formal full-batch automation for the complete 3-IV + 6-cycle sequence

The current workflow is split into two layers:

- `PLC_toolkits_mqtt_NTU`
  Controls PLC/chiller and continuously uploads environment data.
- `MultiModuleTeststandUI`
  Hosts the Flask UI, manual IV controls, DAQ summary, and the new batch automation scripts.

## Main Entry Points

- Web UI: [app.py](./app.py)
- Manual IV page backend: [flask_apps/app_task3.py](./flask_apps/app_task3.py)
- Formal full-batch runner: [scripts/run_full_mmts_batch.py](./scripts/run_full_mmts_batch.py)
- Demo full-batch runner: [scripts/run_full_mmts_batch_demo.py](./scripts/run_full_mmts_batch_demo.py)
- Shared batch status helper: [PythonTools/batch_status.py](./PythonTools/batch_status.py)

## Installation

Use Miniconda or a Python virtual environment on Linux.

Clone the repository and inspect the bootstrap targets:

```bash
git clone git@github.com:ltsai323/MultiModuleTeststandUI.git
cd MultiModuleTeststandUI
make -f makefile_initialize_this_GUI help
```

Important initialization targets:

```bash
make -f makefile_initialize_this_GUI task1a_setup_andrewGUI andrewGUI_install_path=/some/path/to/hgcal-module-testing-gui
make -f makefile_initialize_this_GUI task1b_create_daqclient_service
make -f makefile_initialize_this_GUI task1c_create_output_folder
make -f makefile_initialize_this_GUI task3a_clone_IVscan_codes
make -f makefile_initialize_this_GUI task3b_create_mmts_configuration
make -f makefile_initialize_this_GUI flaska_open_firewall_port5001
make -f makefile_initialize_this_GUI flaskb_make_virtual_environment
make -f makefile_initialize_this_GUI flaskc_make_app_as_system_service
```

You still need to verify and adjust:

- `data/mmts_configurations.yaml`
- `external_packages/hgcal-module-testing-gui/configuration.yaml`
- RS232 resources
- PLC IP / DB settings
- Grafana or embedded monitor URLs

## Run The Web UI

```bash
source .venv/bin/activate
source ./init_bash_vars.sh
.venv/bin/python3 app.py
```

Then open [http://127.0.0.1:5001](http://127.0.0.1:5001).

For standalone local testing of the task3 page only:

```bash
python flask_apps/app_task3.py
```

This starts the IV page on [http://127.0.0.1:5005](http://127.0.0.1:5005).

## Manual Workflow

The existing manual flow is still supported.

1. Start `plc_to_db.py` and keep it running.
2. Start `app.py`.
3. Open the IV page and use `Initialize -> Configure -> Run`.
4. Use `control_hmi.py` manually to start the first cycle and later the remaining 5 cycles.
5. Monitor PLC state, dew point, and IV curves from the web UI / Grafana.

The manual IV flow still goes through:

- `flask_apps/app_task3.py`
- `makefile_task3`
- `scripts/IVscan.initialize.sh`
- `scripts/IVscan.run.sh`

## Demo Full-Batch Automation

The demo runner is meant to validate that the automation sequence itself can run through with tunable parameters.

Files:

- [scripts/run_full_mmts_batch_demo.py](./scripts/run_full_mmts_batch_demo.py)
- [data/full_batch_demo.example.yml](./data/full_batch_demo.example.yml)
- [docs/demo_batch.md](./docs/demo_batch.md)

The demo runner keeps the same dewpoint acquisition method as the main automation:

- read PLC offset `314` for `DMT-01`
- read PLC offset `356` for `DMT-02`
- convert with `1.25 * raw - 5`

For the demo runner, the dewpoint gate uses the original simplified rule:

- compare `min(DMT-01, DMT-02)` against the configured threshold

Demo parameters you can change:

- `demo_controls.dewpoint_threshold_C`
- `cycle_configs.first_cycle.temp_low`
- `cycle_configs.remaining_cycles.temp_low`
- `cycle_configs.remaining_cycles.idle_warm_min`
- `cycle_configs.remaining_cycles.idle_cold_min`
- `demo_controls.dry_run`
- `demo_controls.force_run`

Recommended first validation:

```bash
python scripts/run_full_mmts_batch_demo.py -c data/full_batch_demo.example.yml
```

Suggested demo strategy:

1. Fill one or more `module_ids`.
2. Keep `dry_run: true`.
3. Reduce `temp_low` and cycle hold times.
4. Confirm that the phase transitions and batch status file update as expected.
5. Only then consider switching to real PLC commands.

## Formal Full-Batch Automation

The formal runner is:

- [scripts/run_full_mmts_batch.py](./scripts/run_full_mmts_batch.py)
- [data/full_batch_config.example.yml](./data/full_batch_config.example.yml)

This runner is intended to execute the full sequence:

1. IV1 at room temperature / humidity 50
2. First thermal cycle
3. IV2 during the first low-temperature countdown stage
4. Remaining 5 cycles
5. IV3 after the last cycle

The runner writes shared progress information to:

- `tmp_files/runtime/current_batch_status.json`

The task3 page reads that file and shows a read-only `Auto Batch Status` panel, so the web UI can stay open for human monitoring while the automation runs in the background.

Recommended formal procedure:

1. Confirm `plc_to_db.py` is running.
2. Confirm the task3 page is reachable.
3. Fill the real module IDs into `data/full_batch_config.example.yml` or a copied config.
4. Verify dewpoint rule, cycle configuration, and timeouts.
5. Start the batch runner from the shell.
6. Keep the web UI open for monitoring and manual intervention if needed.

Example:

```bash
python scripts/run_full_mmts_batch.py -c data/full_batch_config.example.yml
```

## Notes

- The automation scripts were added alongside the manual workflow. They do not remove the existing manual path.
- The demo runner and the formal runner are intentionally separate so demo validation can evolve without disturbing the formal sequence.
- The task3 page now exposes batch status for monitoring, but the batch logic itself is still executed by standalone Python scripts rather than by browser actions.
