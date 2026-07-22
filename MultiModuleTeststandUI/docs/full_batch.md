# Task3 Full Batch Automation

The Task3 page provides three batch controls:

- **AutoTest** runs IV1, the first thermal cycle, IV2, the remaining cycles, and IV3.
- **IV3 Test** runs only the final IV scan with the configured module IDs.
- **Clear Modules** clears all module IDs after password confirmation.

AutoTest checks that the PLC is in standby and waits until both dewpoint sensors
are below `precheck.dewpoint_max_C`. Progress is written to
`tmp_files/runtime/current_batch_status.json` and displayed on the Task3 page.

All IV scans in one AutoTest run share one `batch` value. Their iterations are
configured in `data/full_batch_config.example.yml`.

If AutoTest or IV3 Test fails without a user stop request, Task3 automatically
runs `make -f makefile_task3 destroy` and records the result in the batch status
file.
