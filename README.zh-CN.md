# MMTS

[English README](./README.md)

这个仓库主要包含两部分：

- `PLC_toolkits_mqtt_NTU`
  负责 PLC、chiller、环境监控、MQTT 和数据库链路。
- `MultiModuleTeststandUI`
  负责 Flask 网页、IV 扫描控制、DAQ 结果展示，以及新增的批量自动化脚本。

## 仓库里现在有什么

当前这套 MMTS 工作流包含：

- 网页上的手动 IV 扫描
- 基于 PLC 的温度循环控制
- 通过 `plc_to_db.py` 持续进行环境监控
- 用于验证流程能否跑通的 demo 全流程自动化
- 面向完整 3 次 IV + 6 次循环的正式自动化

重要入口文件：

- `PLC_toolkits_mqtt_NTU/plc_to_db.py`
- `PLC_toolkits_mqtt_NTU/control_hmi.py`
- `MultiModuleTeststandUI/app.py`
- `MultiModuleTeststandUI/flask_apps/app_task3.py`
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`

## 手动流程

原来的手动流程仍然保留。

1. 先启动并保持 `PLC_toolkits_mqtt_NTU/plc_to_db.py` 常驻运行。
2. 启动 `MultiModuleTeststandUI/app.py`。
3. 打开 IV 页面，按 `Initialize -> Configure -> Run` 的顺序操作。
4. 用 `control_hmi.py` 手动启动第一次温度循环。
5. 用 `control_hmi.py -c HMI_Control_5cycle.yml` 手动启动后续 5 次循环。
6. 通过网页 / Grafana 观察 PLC 状态、dewpoint 和 IV 曲线。

手动 IV 这条链路仍然走：

- `MultiModuleTeststandUI/flask_apps/app_task3.py`
- `MultiModuleTeststandUI/makefile_task3`
- `MultiModuleTeststandUI/scripts/IVscan.initialize.sh`
- `MultiModuleTeststandUI/scripts/IVscan.run.sh`

## Demo 自动化

demo 版和正式版是分开的。它的目的是先验证自动化编排逻辑能不能跑通，并且允许你自由调整关键参数，而不影响正式版本。

相关文件：

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`
- `MultiModuleTeststandUI/data/full_batch_demo.example.yml`
- `MultiModuleTeststandUI/docs/demo_batch.md`

demo 版 dewpoint 获取方式和主流程保持一致：

- 从 PLC `offset 314` 读取 `DMT-01`
- 从 PLC `offset 356` 读取 `DMT-02`
- 用 `1.25 * raw - 5` 做换算

demo 版 dewpoint 判定使用最开始的简化规则：

- 比较 `min(DMT-01, DMT-02)` 和阈值

demo 版可调参数包括：

- `demo_controls.dewpoint_threshold_C`
- `cycle_configs.first_cycle.temp_low`
- `cycle_configs.remaining_cycles.temp_low`
- `cycle_configs.remaining_cycles.idle_warm_min`
- `cycle_configs.remaining_cycles.idle_cold_min`
- `demo_controls.dry_run`
- `demo_controls.force_run`

建议的第一轮测试命令：

```bash
python MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py -c MultiModuleTeststandUI/data/full_batch_demo.example.yml
```

建议的 demo 验证方式：

1. 先填 1 个或少量 `module_ids`。
2. 保持 `dry_run: true`。
3. 把最低温和保温时间调低、调短。
4. 先确认 phase 切换和 batch status 更新是否正常。
5. 确认流程编排没问题后，再考虑切到真实 PLC 执行。

## 正式完整自动化

正式版入口是：

- `MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- `MultiModuleTeststandUI/data/full_batch_config.example.yml`

它的目标是执行完整流程：

1. IV1：室温 / 湿度 50
2. 第 1 次温度循环
3. IV2：在第一次低温 countdown 阶段运行
4. 后续 5 次温度循环
5. IV3：最后一次循环结束后运行

正式版运行过程中会把共享状态写到：

- `MultiModuleTeststandUI/tmp_files/runtime/current_batch_status.json`

`task3` 页面会读取这个文件，并在网页里显示只读的 `Auto Batch Status` 区域。这样自动脚本在后台跑时，网页仍然可以保持打开供人工监控。

建议的正式操作顺序：

1. 确认 `plc_to_db.py` 正在运行。
2. 确认 `task3` 页面可以访问。
3. 把真实模块编号填入 `full_batch_config.example.yml` 或它的拷贝文件。
4. 检查 dewpoint 规则、循环配置和 timeout。
5. 在命令行启动批量运行脚本。
6. 保持网页打开，便于人工监控和必要时接管。

示例命令：

```bash
python MultiModuleTeststandUI/scripts/run_full_mmts_batch.py -c MultiModuleTeststandUI/data/full_batch_config.example.yml
```

## Windows 本地启动 task3 页面

如果你想在 Windows 上单独启动 `app_task3.py` 做页面测试，可以先进入项目目录，再设置环境变量，并使用项目自己的虚拟环境：

```powershell
cd C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI
$env:AndrewModuleTestingGUI_BASE='C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI\external_packages\hgcal-module-testing-gui'
$env:PYTHONPATH='C:\Users\12784\Documents\mmts\repo\MultiModuleTeststandUI'
.\.venv\Scripts\python.exe .\flask_apps\app_task3.py
```

启动后打开：

- `http://127.0.0.1:5005/`

说明：

- `app.py` 是完整的 MMTS 网页入口，通常使用端口 `5001`
- `flask_apps/app_task3.py` 是单独抽出来做本地测试的 task3 页面，使用端口 `5005`

## 备注

- 新增的自动化脚本是叠加在原有手动流程上的，并没有移除手动流程。
- demo 版和正式版刻意拆开，便于先验证，再上正式流程。
- UI 自己的 README 仍然单独保留在 `MultiModuleTeststandUI/README.md`。
