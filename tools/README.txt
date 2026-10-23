项目本地实验工具
================

Python 环境在项目根目录的 .venv。Finder 默认隐藏点开头的文件；
按 Command + Shift + . 可显示。不要移动或重命名 .venv。

在项目目录的 zsh 终端中运行：
    source ./activate.zsh
这会同时启用 .venv 和 tools/bin，仅影响当前终端。
退出 Python 环境：deactivate

已安装（全部位于本项目 tools 内，无后台服务）：
    fio          3.43，SSD 工作负载与延迟分布测试。
    smartctl     7.5，读取 SSD 健康状态、温度和写入量。
    stream       5.10 参考实现，单线程持续内存带宽测试。
    lat_mem_rd   lmbench 内存访问延迟测试。
    bw_mem       lmbench 内存读写/复制带宽测试。
    tlb          lmbench 基于时延的 TLB 容量推断工具，不是硬件缺失计数器。
    par_mem      lmbench 单线程多条独立访问链的内存级并行度测试。

目录：
    bin/         可运行工具（部分为指向项目源码目录的相对符号链接）。
    src/         上游源码、许可文件、构建产物及原始压缩包。
    logs/        构建日志、安装验证结果；这些不是正式实验数据。
    manifest.json 上游来源、固定版本、提交编号和构建参数。
    rebuild.py   使用现有源码重新编译：python3 tools/rebuild.py

构建说明：
    全部使用本机 Apple Clang，arm64 原生编译。
    lmbench 源码未修改，编译时显式引入 macOS RPC 头文件以适配 Clang。
    lmbench 上游有旧代码警告，日志中保留了原始编译信息。
    STREAM 为单线程构建，每个 double 数组 10,000,000 个元素，10 次迭代。
    STREAM 的 UVA 原站在安装时 DNS 查询失败，使用 README 所注明的 GitHub 镜像。

已验证的能力与限制：
    lat_mem_rd、bw_mem 和 STREAM 已运行通过；STREAM 的数值正确性检查通过。
    tlb 小规模检查正常退出，但没有检测出转折，不能据此给出 TLB 容量。
    par_mem 使用 ENOUGH=1000 的短计时安装检查通过；默认校准较慢。
    上述检查仅用于确认程序能够运行，正式实验需另行设计规模、重复次数和计时。
    FIO 能启动，支持 posixaio；安装测试使用 null 引擎，不访问测试磁盘。
    macOS 下 direct=1、实际队列深度及写入持久性仍需针对测试文件另行验证。
    smartctl 已读到内置 SSD 的健康状态和温度；读取部分 NVMe 错误日志不受支持。
    内存工具不能替代完整 Project 2：并发负载延迟、读写比例矩阵和计数器关联
    仍需项目实验脚本。TLB 硬件事件是否可用也尚未验证。
    macOS 默认页为 16KiB；本机此前 2MiB 大页申请失败，不能声称完成大页对照。

SSD 测试必须指定专用可丢弃文件。不要把写入任务指向系统盘裸设备或现有文件。
本次安装没有运行真实 SSD 写入基准，也没有启用 smartd 或修改 SMART 设置。

正式实验完成后的补充（2026-10-23）：
    上述“安装验证”描述保留作历史记录。三个 project/README.md 是当前正式实验说明。
    Project 2 已通过 Instruments 实测 L1D cache/TLB 和 L2 data-TLB 事件，保留42份原始 trace。
    Project 3 已通过专用文件的 F_NOCACHE CRC32C 读写验证；正式写入总量53.375GiB。
    已发现单进程 POSIX AIO 深度限制并补做多进程只读对照，不把请求深度当作实际深度。
    新设备可使用 python tools/bootstrap.py --build 下载固定版本并在项目内构建。
