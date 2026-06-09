from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from llm_bench.metrics import (
    format_stat,
    format_tpot_value,
    format_tps,
    tpot_ms_to_tps,
)
from llm_bench.runner import BenchmarkRunner, GroupSummary


def _pick(value_p50: float | None, value_mean: float | None) -> float | None:
    return value_p50 if value_p50 is not None else value_mean


def _dual_ms(corrected: float | None, observed: float | None) -> str:
    if corrected is None and observed is None:
        return "n/a"
    lines: list[str] = []
    if corrected is not None:
        lines.append(f"{corrected:.2f}ms")
    if observed is not None:
        lines.append(f"(raw {observed:.2f}ms)")
    return "\n".join(lines)


def _dual_tps(steady: float | None, e2e: float | None) -> str:
    if steady is None and e2e is None:
        return "n/a"
    lines: list[str] = []
    if steady is not None:
        lines.append(format_tps(steady))
    if e2e is not None:
        lines.append(f"(raw {format_tps(e2e)})")
    return "\n".join(lines)


def _ttft_cell(s: GroupSummary) -> str:
    return _dual_ms(
        _pick(s.ttft_corrected.p50, s.ttft_corrected.mean),
        _pick(s.ttft.p50, s.ttft.mean),
    )


def _tps_cell(s: GroupSummary) -> str:
    return _dual_tps(
        _pick(s.decode_tps.p50, s.decode_tps.mean),
        _pick(s.decode_tps_all.p50, s.decode_tps_all.mean),
    )


def _cache_ratio(hit: GroupSummary | None, miss: GroupSummary | None) -> str:
    hit_ttft = None
    miss_ttft = None
    if hit:
        hit_ttft = _pick(hit.ttft_corrected.p50, hit.ttft_corrected.mean) or _pick(
            hit.ttft.p50, hit.ttft.mean
        )
    if miss:
        miss_ttft = _pick(miss.ttft_corrected.p50, miss.ttft_corrected.mean) or _pick(
            miss.ttft.p50, miss.ttft.mean
        )
    if hit_ttft is None or miss_ttft is None or miss_ttft == 0:
        return "n/a"
    return f"{miss_ttft / hit_ttft:.2f}x"


def _reliable_label(s: GroupSummary) -> str:
    if s.total_count == 0:
        return "n/a"
    return f"{s.reliable_count}/{s.total_count}"


def _buffered_label(s: GroupSummary) -> str:
    if s.total_count == 0:
        return "n/a"
    return str(s.buffered_count)


def _decode_summaries(summaries: list[GroupSummary]) -> list[GroupSummary]:
    return [s for s in summaries if s.mode == "decode"]


def build_markdown(summaries: list[GroupSummary], load_summaries: list | None = None) -> str:
    lines = [
        "# LLM API Benchmark Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Latency and Decode",
        "",
        "Each request produces one row (cold=miss, warm=hit). "
        "TTFT and TPS show corrected value on the first line and observed (raw) on the second.",
        "",
    ]

    latency_rows = []
    for s in _decode_summaries(summaries):
        latency_rows.append(
            [
                s.domain,
                s.target_tokens,
                s.cache_mode or "-",
                s.concurrency,
                s.ttft.count,
                _ttft_cell(s).replace("\n", "<br>"),
                _tps_cell(s).replace("\n", "<br>"),
                format_tpot_value(_pick(s.tpot.p50, s.tpot.mean)),
                _buffered_label(s),
                _reliable_label(s),
                format_stat(s.cached_tokens.mean, digits=0),
            ]
        )

    lines.append(
        tabulate(
            latency_rows,
            headers=[
                "domain",
                "target_tokens",
                "cache",
                "concurrency",
                "n",
                "ttft",
                "tps",
                "tpot (ms/tok)",
                "buffered",
                "reliable",
                "cached",
            ],
            tablefmt="github",
        )
    )

    lines.extend(["", "## Prefix Cache TTFT Comparison", ""])
    cache_rows = []
    grouped: dict[tuple[str, int, str, int], dict[str, GroupSummary]] = {}
    for s in _decode_summaries(summaries):
        key = (s.domain, s.target_tokens, s.output_style, s.concurrency)
        grouped.setdefault(key, {})[s.cache_mode or ""] = s

    for (domain, target_tokens, _output_style, concurrency), modes in sorted(grouped.items()):
        hit = modes.get("hit")
        miss = modes.get("miss")
        cache_rows.append(
            [
                domain,
                target_tokens,
                concurrency,
                _ttft_cell(miss).replace("\n", "<br>") if miss else "n/a",
                _ttft_cell(hit).replace("\n", "<br>") if hit else "n/a",
                _cache_ratio(hit, miss),
                format_stat(hit.cached_tokens.mean if hit else None, digits=0),
                format_stat(miss.cached_tokens.mean if miss else None, digits=0),
            ]
        )

    lines.append(
        tabulate(
            cache_rows,
            headers=[
                "domain",
                "target_tokens",
                "concurrency",
                "ttft_miss",
                "ttft_hit",
                "speedup",
                "cached_hit",
                "cached_miss",
            ],
            tablefmt="github",
        )
    )

    if load_summaries:
        lines.extend(["", "## Load / Throughput", ""])
        load_rows = []
        for ls in load_summaries:
            tps_from_tpot = tpot_ms_to_tps(ls.tpot.p50)
            load_rows.append(
                [
                    ls.request_rate,
                    f"{ls.achieved_rate:.2f}",
                    f"{ls.output_throughput:.2f}",
                    f"{ls.goodput:.2f}",
                    format_stat(ls.ttft.p50, suffix=" ms"),
                    format_stat(ls.ttft.p90, suffix=" ms"),
                    format_stat(ls.ttft.p99, suffix=" ms"),
                    format_tpot_value(ls.tpot.p50),
                    format_tpot_value(ls.tpot.p90),
                    format_tps(tps_from_tpot),
                    ls.total_requests,
                    ls.slo_ok_count,
                ]
            )
        lines.append(
            tabulate(
                load_rows,
                headers=[
                    "request_rate",
                    "achieved_rate",
                    "output_tput",
                    "goodput",
                    "ttft_p50",
                    "ttft_p90",
                    "ttft_p99",
                    "tpot_p50 (ms/tok)",
                    "tpot_p90 (ms/tok)",
                    "tps_p50",
                    "total_req",
                    "slo_ok",
                ],
                tablefmt="github",
            )
        )

        lines.extend(["", "## Throughput by Domain", ""])
        domain_rows = []
        for ls in load_summaries:
            for label, stats in sorted(ls.by_domain.items()):
                domain_rows.append(
                    [
                        ls.request_rate,
                        label,
                        f"{stats['output_throughput']:.2f}",
                        stats["request_count"],
                        format_tpot_value(stats["tpot_p50"]),
                        format_tps(stats["tps_p50"]),
                    ]
                )
        if domain_rows:
            lines.append(
                tabulate(
                    domain_rows,
                    headers=[
                        "request_rate",
                        "domain/style",
                        "output_tput",
                        "requests",
                        "tpot_p50 (ms/tok)",
                        "tps_p50",
                    ],
                    tablefmt="github",
                )
            )

    return "\n".join(lines) + "\n"


def print_console(summaries: list[GroupSummary], load_summaries: list | None = None) -> None:
    console = Console()
    table = Table(title="Benchmark Summary")
    for col in [
        "domain",
        "tokens",
        "cache",
        "ccy",
        "ttft",
        "tps",
        "tpot (ms/tok)",
        "buf",
        "rel",
        "cached",
    ]:
        table.add_column(col)

    for s in _decode_summaries(summaries):
        table.add_row(
            s.domain,
            str(s.target_tokens),
            s.cache_mode or "-",
            str(s.concurrency),
            _ttft_cell(s),
            _tps_cell(s),
            format_tpot_value(_pick(s.tpot.p50, s.tpot.mean)),
            _buffered_label(s),
            _reliable_label(s),
            format_stat(s.cached_tokens.mean, digits=0),
        )
    console.print(table)

    if load_summaries:
        load_table = Table(title="Load / Throughput")
        for col in [
            "rate",
            "achieved",
            "out_tput",
            "goodput",
            "ttft_p50",
            "tpot (ms/tok)",
            "tps_p50",
            "reqs",
        ]:
            load_table.add_column(col)
        for ls in load_summaries:
            load_table.add_row(
                str(ls.request_rate),
                f"{ls.achieved_rate:.2f}",
                f"{ls.output_throughput:.2f}",
                f"{ls.goodput:.2f}",
                format_stat(ls.ttft.p50, suffix="ms"),
                format_tpot_value(ls.tpot.p50),
                format_tps(tpot_ms_to_tps(ls.tpot.p50)),
                str(ls.total_requests),
            )
        console.print(load_table)


def write_results(runner: BenchmarkRunner, output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = out / f"raw_{stamp}.json"
    report_path = out / f"report_{stamp}.md"

    payload: dict[str, Any] = runner.to_json()
    raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summaries = runner.summaries()
    load_summaries = runner.load_summaries or None
    report_path.write_text(build_markdown(summaries, load_summaries), encoding="utf-8")
    print_console(summaries, load_summaries)

    latest_raw = out / "raw_latest.json"
    latest_report = out / "report_latest.md"
    latest_raw.write_text(raw_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {"raw": raw_path, "report": report_path}
