# MMTS Demo Batch

This demo flow is separate from the formal automation script.

Files:

- `scripts/run_full_mmts_batch_demo.py`
- `data/full_batch_demo.example.yml`

What can be adjusted in the demo config:

- `demo_controls.dewpoint_threshold_C`
- `cycle_configs.first_cycle.temp_low`
- `cycle_configs.remaining_cycles.temp_low`
- `cycle_configs.remaining_cycles.idle_warm_min`
- `cycle_configs.remaining_cycles.idle_cold_min`

Useful notes:

- The dewpoint readout still comes from PLC offsets `314` and `356`.
- The conversion remains `1.25 * raw - 5`.
- The demo script writes temporary HMI YAML files under `tmp_files/runtime/`.
- By default the demo config uses `dry_run: true` and `force_run: false`, which is safer for workflow validation.

Example:

```bash
python scripts/run_full_mmts_batch_demo.py -c data/full_batch_demo.example.yml
```
