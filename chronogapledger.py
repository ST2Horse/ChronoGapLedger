"""检查逐行 ISO 时间记录中的长间隔、倒序、重复和无效项。"""
import argparse
import json
import math
import re
import sys
from datetime import datetime

VERSION = "0.1.0"
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?", re.ASCII)


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("秒数必须为有限正数")
    return number


def positive_int(value):
    number = int(value)
    if number < 1:
        raise ValueError("必须为大于或等于 1 的整数")
    return number


def parse_stamp(text):
    if not STAMP.fullmatch(text):
        raise ValueError("需要完整日期与时分秒，可带小数秒、Z 或 ±HH:MM 时区")
    return datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)


def inspect_stamps(path, alert_seconds=60, encoding="utf-8-sig", max_details=100):
    alert_seconds = positive_seconds(alert_seconds)
    max_details = positive_int(max_details)
    counts = dict(lines=0, blank_lines=0, valid_timestamps=0, invalid_timestamps=0,
                  compared_pairs=0, gaps=0, backwards=0, duplicates=0, timezone_mismatches=0)
    details = []
    detail_count = 0
    previous = None

    def add(kind, line, **values):
        nonlocal detail_count
        detail_count += 1
        if len(details) < max_details:
            details.append({"kind": kind, "line": line, **values})

    with open(path, encoding=encoding) as source:
        for number, line in enumerate(source, 1):
            counts["lines"] += 1
            text = line.strip()
            if not text:
                counts["blank_lines"] += 1
                continue
            try:
                current = parse_stamp(text)
            except ValueError:
                counts["invalid_timestamps"] += 1
                add("invalid", number, value=text)
                previous = None  # 无效记录切断相邻关系，避免跨越错误行计算。
                continue
            counts["valid_timestamps"] += 1
            if previous is not None:
                old_line, old_time = previous
                if (current.tzinfo is None) != (old_time.tzinfo is None):
                    counts["timezone_mismatches"] += 1
                    add("timezone_mismatch", number, previous_line=old_line)
                else:
                    seconds = (current - old_time).total_seconds()
                    counts["compared_pairs"] += 1
                    if seconds < 0:
                        counts["backwards"] += 1
                        add("backwards", number, previous_line=old_line, seconds=seconds)
                    elif seconds == 0:
                        counts["duplicates"] += 1
                        add("duplicate", number, previous_line=old_line, seconds=0)
                    elif seconds >= alert_seconds:
                        counts["gaps"] += 1
                        add("gap", number, previous_line=old_line, seconds=seconds)
            previous = (number, current)
    return {"tool": "ChronoGapLedger", "version": VERSION, "alert_seconds": alert_seconds,
            **counts, "details": details, "details_truncated": detail_count > len(details),
            "has_findings": detail_count > 0}


def format_report(report):
    lines = [f"ChronoGapLedger {VERSION}", f"Alert seconds: {report['alert_seconds']:g}",
             f"Lines: {report['lines']}; blank: {report['blank_lines']}",
             f"Valid timestamps: {report['valid_timestamps']}",
             f"Invalid timestamps: {report['invalid_timestamps']}",
             f"Compared pairs: {report['compared_pairs']}",
             f"Gaps: {report['gaps']}; backwards: {report['backwards']}; duplicates: {report['duplicates']}",
             f"Timezone mismatches: {report['timezone_mismatches']}"]
    for detail in report["details"]:
        lines.append(json.dumps(detail, ensure_ascii=False, sort_keys=True))
    if report["details_truncated"]:
        lines.append("More details omitted; total counts are complete.")
    if report["valid_timestamps"] < 2:
        lines.append("Too few valid timestamps to infer continuity.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="每行一个完整 ISO 时间戳的文本文件")
    parser.add_argument("--chronogapledger-alert-seconds", type=positive_seconds, default=60,
                        help="相邻时间差达到该秒数时提示，默认 60；必须为有限正数")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--max-details", type=positive_int, default=100)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--version", action="version", version=f"ChronoGapLedger {VERSION}")
    args = parser.parse_args(argv)
    if args.gui:
        from tool_window import run_window
        run_window("ChronoGapLedger", "间隔提醒秒数（正数）", "60", inspect_stamps, format_report)
        return 0
    if not args.file:
        parser.error("需要提供时间记录文件路径，或使用 --gui")
    try:
        report = inspect_stamps(args.file, args.chronogapledger_alert_seconds,
                                args.encoding, args.max_details)
    except (OSError, UnicodeError, LookupError, ValueError, OverflowError) as error:
        print(f"ChronoGapLedger: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    return 1 if report["has_findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
