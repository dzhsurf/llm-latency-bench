#!/usr/bin/env python3
"""Development-time combiner for static benchmark datasets (does not author content)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.seeds import (
    CODING_NORMAL_TASKS,
    CODING_SEEDS,
    CODING_STRUCTURED_TASKS,
    DOC_NORMAL_TASKS,
    DOC_SEEDS,
    DOC_STRUCTURED_TASKS,
    MATH_NORMAL_INSTRUCTIONS,
    MATH_SEEDS,
    MATH_STRUCTURED_INSTRUCTIONS,
    WRITING_NORMAL_INSTRUCTIONS,
    WRITING_SEEDS,
    WRITING_STRUCTURED_INSTRUCTIONS,
)
from tools.seeds.combine import assemble_prompt, build_body, rotate_seeds, select_for_target

COUNT_TOKENS_URL = "http://127.0.0.1:7575/anthropic/v1/messages/count_tokens"
MODEL = "glm-4.7"
TARGET_LENGTHS = [1024, 4096, 8192, 16384, 32768, 65536, 131072]
CASES_PER_LENGTH = 10
NORMAL_CASES = 5
TOLERANCE = 0.05
DATASETS_DIR = ROOT / "datasets"

CODING_HEADER = "You are reviewing a repository of independent software modules."
DOC_HEADER = "Read the following reference materials and complete the analysis task."


def output_style_for_case(case_index: int) -> str:
    return "normal" if case_index <= NORMAL_CASES else "structured"


def task_for_case(normal_tasks: list[str], structured_tasks: list[str], case_index: int) -> str:
    if case_index <= NORMAL_CASES:
        return normal_tasks[case_index - 1]
    return structured_tasks[case_index - NORMAL_CASES - 1]


def count_tokens(prompt: str) -> int:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": "EMPTY",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(COUNT_TOKENS_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return int(resp.json()["input_tokens"])


def write_item(
    domain: str,
    target: int,
    case_index: int,
    prompt: str,
    task: str,
    measured: int,
    seed_ids: list[str],
    *,
    output_style: str,
) -> dict:
    rel_dir = domain
    out_dir = DATASETS_DIR / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    size_label = f"{target // 1024}k"
    filename = f"{domain}_{size_label}_{case_index:02d}.json"
    rel_path = f"{rel_dir}/{filename}"
    file_path = DATASETS_DIR / rel_path
    file_path.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "task": task,
                "output_style": output_style,
                "seed_ids": seed_ids,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "id": f"{domain}_{target}_{case_index:02d}",
        "domain": domain,
        "target_tokens": target,
        "case_index": case_index,
        "output_style": output_style,
        "measured_tokens": measured,
        "seed_ids": seed_ids,
        "path": rel_path,
    }


def case_start_index(case_index: int, target: int, domain_offset: int) -> int:
    return (case_index * 17 + (target // 1024) * 3 + domain_offset) % 1000


def generate_seed_based_domain(
    domain: str,
    seeds: list,
    normal_tasks: list[str],
    structured_tasks: list[str],
    header: str,
    *,
    domain_offset: int,
    manifest_items: list[dict],
) -> None:
    for target in TARGET_LENGTHS:
        print(f"[{domain}] target={target}, cases={CASES_PER_LENGTH}")
        for case in range(1, CASES_PER_LENGTH + 1):
            output_style = output_style_for_case(case)
            task = task_for_case(normal_tasks, structured_tasks, case)
            start = case_start_index(case, target, domain_offset) % len(seeds)
            selected, prompt, task, measured, size_hint = select_for_target(
                seeds,
                target_tokens=target,
                count_tokens=count_tokens,
                header=header,
                task=task,
                start_index=start,
            )
            seed_ids = [s.id for s in selected]
            if case == 1:
                print(f"  size_hint={size_hint}")
            manifest_items.append(
                write_item(
                    domain,
                    target,
                    case,
                    prompt,
                    task,
                    measured,
                    seed_ids,
                    output_style=output_style,
                )
            )
            print(
                f"  case {case:02d} ({output_style}): seeds={seed_ids[:3]}... measured={measured}"
            )


def build_rotating_prompt(
    seeds: list,
    *,
    header: str,
    case_index: int,
    focus_seed,
    focus_instruction: str,
) -> tuple[str, str, int, list[str]]:
    ordered = rotate_seeds(seeds, case_index - 1)
    body = build_body(ordered)
    task = f"{focus_instruction} Primary focus: '{focus_seed.title}'."
    prompt = assemble_prompt(header, body, task)
    measured = count_tokens(prompt)
    seed_ids = [s.id for s in ordered]
    return prompt, task, measured, seed_ids


def generate_all() -> None:
    manifest_items: list[dict] = []
    started = time.time()

    generate_seed_based_domain(
        "coding",
        CODING_SEEDS,
        CODING_NORMAL_TASKS,
        CODING_STRUCTURED_TASKS,
        CODING_HEADER,
        domain_offset=0,
        manifest_items=manifest_items,
    )
    generate_seed_based_domain(
        "doc_analysis",
        DOC_SEEDS,
        DOC_NORMAL_TASKS,
        DOC_STRUCTURED_TASKS,
        DOC_HEADER,
        domain_offset=50,
        manifest_items=manifest_items,
    )

    print(f"[math] target=1024, cases={CASES_PER_LENGTH}")
    for case in range(1, CASES_PER_LENGTH + 1):
        output_style = output_style_for_case(case)
        focus = MATH_SEEDS[case - 1]
        if output_style == "normal":
            instruction = MATH_NORMAL_INSTRUCTIONS[case - 1]
        else:
            instruction = MATH_STRUCTURED_INSTRUCTIONS[case - NORMAL_CASES - 1]
        prompt, task, measured, seed_ids = build_rotating_prompt(
            MATH_SEEDS,
            header="Mathematics exam booklet. Solve the primary problem with full reasoning.",
            case_index=case,
            focus_seed=focus,
            focus_instruction=instruction,
        )
        manifest_items.append(
            write_item(
                "math",
                1024,
                case,
                prompt,
                task,
                measured,
                seed_ids,
                output_style=output_style,
            )
        )
        print(f"  case {case:02d} ({output_style}): focus={focus.id} measured={measured}")

    print(f"[writing] target=1024, cases={CASES_PER_LENGTH}")
    for case in range(1, CASES_PER_LENGTH + 1):
        output_style = output_style_for_case(case)
        focus = WRITING_SEEDS[case - 1]
        if output_style == "normal":
            instruction = WRITING_NORMAL_INSTRUCTIONS[case - 1]
        else:
            instruction = WRITING_STRUCTURED_INSTRUCTIONS[case - NORMAL_CASES - 1]
        prompt, task, measured, seed_ids = build_rotating_prompt(
            WRITING_SEEDS,
            header="Creative writing workbook. Complete the primary assignment.",
            case_index=case,
            focus_seed=focus,
            focus_instruction=instruction,
        )
        manifest_items.append(
            write_item(
                "writing",
                1024,
                case,
                prompt,
                task,
                measured,
                seed_ids,
                output_style=output_style,
            )
        )
        print(f"  case {case:02d} ({output_style}): focus={focus.id} measured={measured}")

    manifest = {
        "model_used_for_counting": MODEL,
        "count_tokens_url": COUNT_TOKENS_URL,
        "tolerance": TOLERANCE,
        "cases_per_length": CASES_PER_LENGTH,
        "normal_cases": NORMAL_CASES,
        "items": manifest_items,
    }
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    (DATASETS_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Done in {time.time() - started:.1f}s, wrote {len(manifest_items)} items")


if __name__ == "__main__":
    generate_all()
