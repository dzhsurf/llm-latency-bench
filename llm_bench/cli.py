from __future__ import annotations

import argparse
import asyncio
import sys

from llm_bench.config import BenchConfig
from llm_bench.report import write_results
from llm_bench.runner import BenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM API performance benchmark tool")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--domain", default=None, help="Run only one domain")
    parser.add_argument("--length", type=int, default=None, help="Run only one target token length")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logs")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = BenchConfig.load(args.config)
    runner = BenchmarkRunner(config, verbose=not args.quiet)
    asyncio.run(runner.run(domain_filter=args.domain, length_filter=args.length))
    paths = write_results(runner, config.output.dir)
    print(f"Wrote raw results to {paths['raw']}")
    print(f"Wrote report to {paths['report']}")


if __name__ == "__main__":
    sys.exit(main())
