# MMTS

[English README](./README.md)

这个仓库主要包含两部分：

- `PLC_toolkits_mqtt_NTU`
  负责 PLC、chiller、温循控制、环境监控、MQTT 和数据库相关工具。
- `MultiModuleTeststandUI`
  负责 Flask 网页、IV scan 控制、DAQ 结果展示，以及 batch 自动化脚本。

日常大多数 MMTS 操作都应该进入：

```bash
cd MultiModuleTeststandUI
```

因为很多命令依赖相对路径，例如 `data/`、`scripts/`、`makefile_task3` 和 `tmp_files/runtime/`。

## 常用启动

```bash
cd MultiModuleTeststandUI
source .venv/bin/activate
source ./init_bash_vars.sh
python3 app.py
```

打开：

```text
http://127.0.0.1:5001
```

## 网页上的 IV Scan

网页 task3 的手动 IV 流程是：

```text
Initialize -> 扫 module ID -> Configure -> Run
```

`Run` 按钮只跑一次 IV scan，底层调用：

```bash
make -f makefile_task3 run
```

## 网页上的 AutoTest

`AutoTest` 按钮用于从网页启动正式 full-batch 流程。

点击 `AutoTest` 后会：

1. 校验并保存当前网页表单。
2. 保存你扫进去的 module ID。
3. 生成 `MultiModuleTeststandUI/tmp_files/runtime/full_batch_web.yml`。
4. 调用 `scripts/run_full_mmts_batch.py`。
5. 把状态写入 `tmp_files/runtime/current_batch_status.json`。
6. 网页 `Auto Batch Status` 面板显示当前 batch 状态。

`full_batch_web.yml` 是落盘文件，杀掉并重启 `app.py` 后文件仍然存在；但是网页表单和 Flask 内存里的配置会被清空。下一次点击 `AutoTest` 会覆盖这个文件。

也就是说，`AutoTest` 已经包含网页配置步骤。保存网页表单之后，它等价于在 `MultiModuleTeststandUI` 目录下运行：

```bash
python scripts/run_full_mmts_batch.py \
  -c tmp_files/runtime/full_batch_web.yml \
  --status-file tmp_files/runtime/current_batch_status.json
```

正式 runner 在每一次 IV scan 前也会自动执行：

```bash
make -f makefile_task3 initialize
```

## Demo 和正式版区别

Demo 版：

- 脚本：`MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`
- 配置：`MultiModuleTeststandUI/data/full_batch_demo.example.yml`
- 特点：温度、cycle、idle time、dewpoint threshold 和 module ID 都集中在一个 YAML 里，适合调试和验证流程。

正式版：

- 脚本：`MultiModuleTeststandUI/scripts/run_full_mmts_batch.py`
- 配置：`MultiModuleTeststandUI/data/full_batch_config.example.yml`
- 特点：目标是生产用完整流程；当前网页 `AutoTest` 已经走正式 runner，并用网页扫到的 module ID 覆盖正式配置里的 `module_ids`。

## Batch 流程概要

当前 demo/full-batch 目标流程是：

```text
precheck
-> 等 dewpoint
-> IV1
-> 第一轮温循
-> 等 cooling down
-> 等 cooling countdown
-> IV2
-> 等回 standby
-> 后续 5 轮温循
-> 等回 standby
-> IV3
```

PLC status code 来自 `PLC_toolkits_mqtt_NTU/plc_io.py`：

```text
0 = door open
1 = standby
2 = countdown warming
3 = warming up
4 = countdown cooling
5 = cooling down
```

现在 batch runner 没有把 `code 3 warming up` 当作单独 checkpoint，但 warming 参数仍然会通过 `temp_high` 和 `idle_warm_min` 写入 PLC/HMI config。

## 重要文件

- `MultiModuleTeststandUI/app.py`: 主网页入口。
- `MultiModuleTeststandUI/flask_apps/app_task3.py`: IV scan 后端和 AutoTest 路由。
- `MultiModuleTeststandUI/templates/index_task3.html`: task3 页面按钮和状态显示。
- `MultiModuleTeststandUI/makefile_task3`: 单次 IV scan。
- `MultiModuleTeststandUI/scripts/run_full_mmts_batch_demo.py`: demo batch 自动化。
- `MultiModuleTeststandUI/data/full_batch_demo.example.yml`: demo batch 配置。
- `PLC_toolkits_mqtt_NTU/control_hmi.py`: PLC/HMI 温循控制入口。
- `PLC_toolkits_mqtt_NTU/plc_io.py`: PLC 读写和 status code 计算。

## 依赖说明

- `pymeasure` 固定为 `0.14.0`，避免新版 Keithley 2400 实现变化影响当前代码。
- Python 中 `import snap7` 对应 pip 包名是 `python-snap7`；当前安装约束为 `python-snap7<3`。
