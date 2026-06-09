from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from llm_bench.config import BenchConfig
from llm_bench.report import write_session_final
from llm_bench.runner import BenchmarkRunner
from llm_bench.session import (
    SessionStore,
    config_fingerprint,
    generate_session_id,
    plan_units,
)

_active_session: SessionStore | None = None


def _sigint_handler(_signum: int, _frame: object) -> None:
    if _active_session is not None:
        report = _active_session.path / "report.md"
        print(
            f"\nInterrupted. Checkpoint saved; partial report: {report}",
            file=sys.stderr,
        )
    raise SystemExit(130)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM API performance benchmark tool")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--domain", default=None, help="Run only one domain")
    parser.add_argument("--length", type=int, default=None, help="Run only one target token length")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logs")
    session = parser.add_mutually_exclusive_group()
    session.add_argument(
        "--session",
        metavar="ID",
        help="Start a new run with this session id (must not already exist)",
    )
    session.add_argument(
        "--resume",
        metavar="ID",
        help="Resume an existing session under results/ID/",
    )
    return parser


def _validate_resume_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.resume and (args.domain or args.length is not None):
        parser.error("--resume cannot be used with --domain or --length")


def main(argv: list[str] | None = None) -> None:
    global _active_session

    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_resume_args(parser, args)

    config = BenchConfig.load(args.config)
    runner = BenchmarkRunner(config, verbose=not args.quiet)

    if config.load_test.enabled:
        asyncio.run(runner.run(domain_filter=args.domain, length_filter=args.length))
        session_id = args.session or generate_session_id()
        session_path = Path(config.output.dir) / session_id
        paths = write_session_final(runner, session_path)
        print(f"Wrote raw results to {paths['raw']}")
        print(f"Wrote report to {paths['report']}")
        return

    signal.signal(signal.SIGINT, _sigint_handler)

    if args.resume:
        store = SessionStore.load(config.output.dir, args.resume)
        fresh_fp = config_fingerprint(config, store.meta["planned_units"])
        if fresh_fp != store.meta["config_fingerprint"]:
            parser.error(
                "Config fingerprint mismatch: workload in --config differs from the "
                "saved session. Use the original config or start a new session."
            )
        stored_path = store.meta.get("config_path")
        if stored_path and Path(stored_path).resolve() != Path(args.config).resolve():
            print(
                f"Warning: --config {args.config!r} differs from session "
                f"config_path {stored_path!r}; using session snapshot.",
                file=sys.stderr,
            )
        runner = BenchmarkRunner(store.config_from_meta(), verbose=not args.quiet)
        _active_session = store
        print(f"Resuming session {store.session_id}  ({store.completed_count}/{store.total_units} done)")
        print(f"  → {store.path}/")
        asyncio.run(runner.run(session=store))
    else:
        session_id = args.session or generate_session_id()
        items = runner._filter_items_for_run(
            domain_filter=args.domain,
            length_filter=args.length,
        )
        if not items:
            runner.log.no_items()
            return

        planned_units = plan_units(items, config.run.concurrency_levels)
        store = SessionStore.create(
            config.output.dir,
            session_id,
            config=config,
            config_path=str(Path(args.config).resolve()),
            planned_units=planned_units,
        )
        _active_session = store
        print(f"Session: {session_id}  →  {store.path}/")
        asyncio.run(
            runner.run(
                session=store,
                domain_filter=args.domain,
                length_filter=args.length,
            )
        )

    paths = write_session_final(runner, _active_session.path)
    print(f"Wrote raw results to {paths['raw']}")
    print(f"Wrote report to {paths['report']}")


if __name__ == "__main__":
    sys.exit(main())
