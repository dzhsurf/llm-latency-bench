from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from llm_bench.clients.base import StreamResult
from llm_bench.config import BenchConfig
from llm_bench.datasets import DatasetItem
from llm_bench.metrics import LoadSummary, format_tpot_value, format_tps


def _fmt_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1000:
        return f"{value / 1000:.2f}s"
    return f"{value:.0f}ms"


def _fmt_tps(value: float | None) -> str:
    return format_tps(value)


def _fmt_tokens(value: int) -> str:
    if value >= 1024:
        return f"{value / 1024:.1f}k"
    return str(value)


def _context_label(tokens: int) -> str:
    if tokens >= 1024 and tokens % 1024 == 0:
        return f"{tokens // 1024}k"
    return _fmt_tokens(tokens)


class BenchConsole:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.console = Console(stderr=False)

    def _print(self, *args, **kwargs) -> None:
        if self.enabled:
            self.console.print(*args, **kwargs)

    def banner(self, config: BenchConfig, *, item_count: int, domain_filter: str | None, length_filter: int | None) -> None:
        ep = config.endpoint
        run = config.run
        domains = ", ".join(config.matrix.domains)
        lengths = ", ".join(_context_label(t) for t in config.matrix.context_lengths)
        filters: list[str] = []
        if domain_filter:
            filters.append(f"domain={domain_filter}")
        if length_filter is not None:
            filters.append(f"length={_context_label(length_filter)}")
        filter_line = f"\nFilters: {', '.join(filters)}" if filters else ""

        body = (
            f"Endpoint: {ep.base_url} ({ep.api_type})\n"
            f"Model: {ep.model}\n"
            f"Items: {item_count}  |  Repeats: {run.repeats}  |  Warmup: {run.warmup}\n"
            f"Decode max tokens: {run.decode_max_tokens}\n"
            f"Domains: {domains}\n"
            f"Context lengths: {lengths}\n"
            f"Prefix caching: {'on' if config.matrix.test_prefix_caching else 'off'}"
            f"{filter_line}"
        )
        self._print(Panel(body, title="LLM Benchmark", border_style="cyan"))

    def load_banner(self, config: BenchConfig, *, item_count: int) -> None:
        load = config.load_test
        rates = ", ".join(str(r) for r in load.request_rate_sweep)
        body = (
            f"Endpoint: {config.endpoint.base_url} ({config.endpoint.api_type})\n"
            f"Model: {config.endpoint.model}\n"
            f"Items: {item_count}  |  Duration: {load.duration_s}s  |  Warmup: {load.warmup_s}s\n"
            f"Request rates: {rates}\n"
            f"Cache hit ratio: {load.cache_hit_ratio:.0%}\n"
            f"Max concurrency: {load.max_concurrency or 'unlimited'}"
        )
        self._print(Panel(body, title="Load Test", border_style="magenta"))

    def item_start(
        self,
        *,
        index: int,
        total: int,
        item: DatasetItem,
        concurrency: int,
    ) -> None:
        ctx = _context_label(item.target_tokens)
        ccy = f"  ccy={concurrency}" if concurrency > 1 else ""
        self._print(
            f"\n[bold cyan][{index}/{total}][/bold cyan] "
            f"[bold]{item.domain}[/bold]  ctx={ctx}  "
            f"case={item.case_index:02d}  style={item.output_style}"
            f"{ccy}  "
            f"[dim]({item.measured_tokens:,} input tokens)[/dim]"
        )

    def repeat_start(self, *, repeat_index: int, repeats: int) -> None:
        self._print(f"  [dim]repeat {repeat_index + 1}/{repeats}[/dim]")

    def warmup(self, *, round_index: int, total: int) -> None:
        self._print(f"  [dim]warmup {round_index + 1}/{total}[/dim]")

    def request_start(self, *, label: str, cache_mode: str, max_tokens: int) -> None:
        self._print(
            f"    [yellow]→[/yellow] {label} "
            f"[dim](cache={cache_mode}, max_tokens={max_tokens})[/dim] ..."
        )

    def request_done(self, *, label: str, result: StreamResult, elapsed_s: float) -> None:
        ttft_display = result.ttft_corrected_ms if result.ttft_corrected_ms is not None else result.ttft_ms
        parts = [
            f"ttft={_fmt_ms(ttft_display)}",
            f"latency={_fmt_ms(result.total_latency_ms)}",
            f"out={result.output_tokens}",
        ]
        if (
            result.ttft_ms is not None
            and result.ttft_corrected_ms is not None
            and abs(result.ttft_ms - result.ttft_corrected_ms) > 1
        ):
            parts.append(f"raw={_fmt_ms(result.ttft_ms)}")
        if result.decode_tps is not None:
            parts.append(f"tps={_fmt_tps(result.decode_tps)}")
        if result.decode_tps_e2e is not None:
            parts.append(f"[dim]e2e={_fmt_tps(result.decode_tps_e2e)}[/dim]")
        if result.tpot_ms is not None:
            parts.append(f"tpot={format_tpot_value(result.tpot_ms)} ms/tok")
        if result.decode_buffered:
            parts.append("[buffered]")
        elif not result.decode_reliable and result.decode_tps is not None:
            parts.append("[unreliable]")
        if result.cached_tokens:
            parts.append(f"cached={_fmt_tokens(result.cached_tokens)}")
        if result.input_tokens:
            parts.append(f"in={_fmt_tokens(result.input_tokens)}")

        style = "red" if result.error else "green"
        detail = "  ".join(parts)
        if result.error:
            detail += f"  [red]error: {result.error}[/red]"
        self._print(
            f"    [{style}]✓[/{style}] {label}  {detail}  "
            f"[dim]({elapsed_s:.1f}s wall)[/dim]"
        )

    def throughput_start(self, *, concurrency: int) -> None:
        self._print(f"  [dim]throughput x{concurrency}[/dim]")

    def load_point_start(self, *, rate: float, duration_s: int) -> None:
        rate_label = "inf" if rate == float("inf") else f"{rate:.1f}/s"
        self._print(f"\n[bold magenta]Load point[/bold magenta]  rate={rate_label}  duration={duration_s}s")

    def load_progress(
        self,
        *,
        elapsed_s: float,
        duration_s: int,
        in_flight: int,
        completed: int,
    ) -> None:
        self._print(
            f"  [dim]load {elapsed_s:.0f}/{duration_s}s  "
            f"in_flight={in_flight}  completed={completed}[/dim]"
        )

    def load_point_done(self, *, summary: LoadSummary) -> None:
        self._print(
            f"  [green]done[/green]  achieved={summary.achieved_rate:.2f}/s  "
            f"out_tput={summary.output_throughput:.2f} tok/s  "
            f"goodput={summary.goodput:.2f}/s  "
            f"reqs={summary.total_requests}  slo_ok={summary.slo_ok_count}"
        )

    def done(self, *, record_count: int, elapsed_s: float) -> None:
        self._print(
            Panel(
                f"Collected {record_count} records in {elapsed_s:.1f}s",
                title="Done",
                border_style="green",
            )
        )

    def no_items(self) -> None:
        self._print("[yellow]No dataset items matched the current filters.[/yellow]")
