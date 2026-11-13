# ChronoGapLedger

ChronoGapLedger 是一个本地时间记录检查工具。读取每行一个 ISO 时间戳的文本，按文件原有顺序报告长间隔、倒序、重复时间和无效项。适合检查定时采样记录、任务执行时间清单或从日志中导出的时间列。程序不修改文件，不自动排序，也不访问网络。

版本 0.1.0；需要 Python 3.10 或以上，仅使用标准库。窗口版还需要 Tkinter。

## 下载与运行

- 项目主页：https://github.com/ST2Horse/ChronoGapLedger
- ZIP 下载：https://github.com/ST2Horse/ChronoGapLedger/archive/refs/heads/main.zip

下载后完整解压。Windows 用户可双击 `打开工具.cmd`，选择时间记录文件后点击“开始检查”。该启动方式要求 `python` 命令可用，并已安装 Tkinter。窗口可修改编码和提醒秒数。

在工具目录中打开终端，运行：

```powershell
python chronogapledger.py demo/stamps.txt
python chronogapledger.py demo/stamps.txt --chronogapledger-alert-seconds 120
python chronogapledger.py demo/stamps.txt --json
python chronogapledger.py --gui
```

## 输入格式

每行只放一个完整时间戳，可以有首尾空白。支持这些形式：

```text
2026-11-01T10:00:00
2026-11-01 10:00:00
2026-11-01T10:00:00.500000Z
2026-11-01T18:00:00+08:00
```

日期和时分秒必填。小数秒支持 1–6 位；时区可省略，或使用大写 `Z`、`+HH:MM`、`-HH:MM`。不支持 Unix 数值时间戳、只有日期、时区名称，以及时间后附带的日志正文。

## 一个实际例子

附带的 `demo/stamps.txt` 内容为：

```text
2026-11-01T10:00:00Z
2026-11-01T10:00:30Z
2026-11-01T10:02:00Z
2026-11-01T10:01:50Z
not-a-timestamp
2026-11-01T10:05:00Z
2026-11-01T10:05:10Z
```

运行 `python chronogapledger.py demo/stamps.txt` 得到：

```text
ChronoGapLedger 0.1.0
Alert seconds: 60
Lines: 7; blank: 0
Valid timestamps: 6
Invalid timestamps: 1
Compared pairs: 4
Gaps: 1; backwards: 1; duplicates: 0
Timezone mismatches: 0
{"kind": "gap", "line": 3, "previous_line": 2, "seconds": 90.0}
{"kind": "backwards", "line": 4, "previous_line": 3, "seconds": -10.0}
{"kind": "invalid", "line": 5, "value": "not-a-timestamp"}
```

第 2、3 行相差 90 秒，触发默认 60 秒的提醒；第 4 行比第 3 行早 10 秒，是倒序；第 5 行无法解析。无效行会切断相邻关系，因此不计算第 4 行到第 6 行的间隔。

## 特有参数怎么用

`--chronogapledger-alert-seconds S` 设置长间隔提醒的秒数，默认 60。相邻时间差**大于或等于** S 时报告 `gap`，S 必须为有限正数，可以是小数。

上例改为 `--chronogapledger-alert-seconds 120` 后，90 秒的间隔不再触发 `gap`；倒序和无效时间仍然报告。这个参数不改变文件顺序、不改写时间，也不控制倒序或重复时间的判断。

## 参数

| 参数 | 用途 |
| --- | --- |
| `file` | 每行一个完整时间戳的文本文件 |
| `--chronogapledger-alert-seconds S` | 长间隔提醒秒数，默认 60，含等于边界 |
| `--encoding NAME` | 输入编码，默认 `utf-8-sig` |
| `--max-details N` | 最多展示 N 条异常明细，默认 100；总数仍完整统计 |
| `--json` | 在终端输出 JSON 报告 |
| `--gui` | 打开窗口，明细上限使用默认 100 |
| `--version` | 显示版本 |

## 比较规则与限制

- 按文件原有顺序比较，不自动排序。空行跳过，不切断相邻关系；无效时间行会切断相邻关系。
- 两个带时区偏移的时间按实际时间点比较。例如 `08:00:00+08:00` 和同日 `00:00:00Z` 为同一时刻，记为重复。
- 两个不带时区的时间按字面日期和时间比较，不推测时区或夏令时。相邻两项只有一项带时区时，报告 `timezone_mismatch`，不计算该对间隔；之后继续从当前项向后比较。
- 负差值记为倒序，0 秒记为重复，正差值达到提醒秒数时记为长间隔。倒序后继续从该条记录向后比较。
- 无效时间会记录原行文字，其他异常记录行号和秒数；分享报告前检查是否包含私人内容。
- 按行读取，异常明细默认保留前 100 条；报告明确标出是否省略明细，计数不受上限影响。
- 长间隔不等于已经证明丢失数据；需要结合设备采样周期和任务安排判断。0 个长间隔也不保证采样完整。
- 空文件允许读取，但会提示有效时间不足；少于两条有效时间不能据此判断连续性。
- 命令行退出码：0 表示检查完成且没有上述异常；1 表示完成但有异常；2 表示文件、编码或参数错误。演示文件返回 1 是预期结果。

## 测试

```powershell
python -m unittest discover -s tests -v
```

覆盖秒数边界、小数秒、时区换算、倒序、重复、空行、无效行切断、非法日期、明细上限、空文件与退出码，并检查输入内容未改变。
