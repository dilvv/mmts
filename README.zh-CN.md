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

手动 `Run` 会使用网页上选择的温度和湿度。

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

`AutoTest` 不使用网页上的温度和湿度控件。它使用 `data/full_batch_config.example.yml` 里的正式 batch IV 设置。

如果 IV 初始化时发现 VITREK 或 Keithley RS232 设备没有连接，AutoTest 会自动执行：

```bash
make -f makefile_task3 destroy
```

并把网页 server 状态切到 `destroyed`。

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
-> IV1
-> 等 dewpoint
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

## 从上游同步 MultiModuleTeststandUI

原作者的 UI 仓库已经登记为：

```text
upstream-ui = git@github.com:ltsai323/MultiModuleTeststandUI.git
```

下面的流程只更新本仓库中的 `MultiModuleTeststandUI/` 子目录，不会修改
`PLC_toolkits_mqtt_NTU/`。

同步前应保证工作区干净，并从本仓库根目录执行：

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

每条命令的作用：

- `cd mmts`：进入同时包含 `MultiModuleTeststandUI/` 和
  `PLC_toolkits_mqtt_NTU/` 的根仓库。
- `git switch main`：切换到本地 `main` 分支。
- `git pull --ff-only origin main`：从自己的 GitHub 仓库
  `dilvv/mmts` 更新本地 `main`。如果本地和远程已经分叉，命令会停止，
  不会擅自生成合并提交。
- `git fetch upstream-ui`：下载原作者仓库的最新分支和提交历史，但不修改
  当前文件。
- `git switch -c sync-upstream-ui`：从当前 `main` 创建临时同步分支，
  避免未经测试的上游更新直接进入本地 `main`。
- `git subtree pull --prefix=MultiModuleTeststandUI upstream-ui main --squash`：
  把原作者仓库 `main` 分支的更新合并到本仓库的
  `MultiModuleTeststandUI/` 目录；`--squash` 会把本次上游更新记录为一个
  同步提交。

同步完成后，应先测试 GUI。确认正常后再合并并推送到自己的仓库：

```bash
git switch main
git merge --ff-only sync-upstream-ui
git push origin main
git branch -d sync-upstream-ui
```

如果双方修改的是不同位置，Git 通常会自动合并；如果双方修改了同一位置，
Git 会停止并标记冲突，等待人工决定，不会静默覆盖本地修改。

执行这些命令的机器必须安装 `git-subtree`。部分 Git for Windows 安装包
没有包含该组件；如果 Linux 测试机提示找不到 `git subtree`，需要先安装
`git-subtree` 软件包。
