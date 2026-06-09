from __future__ import annotations

from collections.abc import Callable, Sequence

from tools.seeds.types import Seed

TOLERANCE = 0.05


def within_tolerance(measured: int, target: int, tolerance: float = TOLERANCE) -> bool:
    low = int(target * (1 - tolerance))
    high = int(target * (1 + tolerance))
    return low <= measured <= high


def rotate_seeds(seeds: Sequence[Seed], start_index: int) -> list[Seed]:
    n = len(seeds)
    start = start_index % n
    return list(seeds[start:]) + list(seeds[:start])


def build_body(seeds: Sequence[Seed]) -> str:
    return "\n\n".join(f"## {seed.title}\n{seed.body}" for seed in seeds)


def assemble_prompt(header: str, body: str, task: str) -> str:
    return f"{header}\n\n{body}\n\nTask: {task}"


def select_seed_count(
    seeds: Sequence[Seed],
    *,
    target_tokens: int,
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
    start_index: int,
) -> tuple[list[Seed], str, str, int]:
    """Pick a non-repeating rotated subset of seeds to approach target token length."""
    ordered = rotate_seeds(seeds, start_index)
    best_selected: list[Seed] = []
    best_prompt = ""
    best_measured = 0

    selected: list[Seed] = []
    for seed in ordered:
        trial = selected + [seed]
        body = build_body(trial)
        prompt = assemble_prompt(header, body, task)
        measured = count_tokens(prompt)
        if measured > int(target_tokens * (1 + TOLERANCE)) and selected:
            break
        selected = trial
        if within_tolerance(measured, target_tokens) or abs(measured - target_tokens) < abs(
            best_measured - target_tokens
        ):
            best_selected = list(selected)
            best_prompt = prompt
            best_measured = measured
        if within_tolerance(measured, target_tokens):
            return selected, prompt, task, measured

    if not best_selected:
        seed = ordered[0]
        body = build_body([seed])
        best_prompt = assemble_prompt(header, body, task)
        best_measured = count_tokens(best_prompt)
        return [seed], best_prompt, task, best_measured

    return best_selected, best_prompt, task, best_measured


def build_body_volumes(
    seeds: Sequence[Seed],
    *,
    volumes: int,
    start_index: int,
) -> tuple[str, list[Seed]]:
    """Repeat the full rotated seed catalog across volumes with distinct ordering."""
    used: list[Seed] = []
    parts: list[str] = []
    n = len(seeds)
    for vol in range(volumes):
        vol_start = (start_index + vol * 11) % n
        ordered = rotate_seeds(seeds, vol_start)
        used.extend(ordered)
        if vol > 0:
            parts.append(f"--- Volume {vol + 1} (continued reference) ---")
        parts.append(build_body(ordered))
    return "\n\n".join(parts), used


def calibrate_volumes(
    seeds: Sequence[Seed],
    *,
    target_tokens: int,
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
    start_index: int = 0,
) -> int:
    low, high = 1, max(1, (target_tokens // max(1, _estimate_single_pass_tokens(seeds, count_tokens, header, task))) + 2)
    high = min(high, 64)
    best_volumes = 1
    best_delta = 10**9

    while low <= high:
        mid = (low + high) // 2
        body, _ = build_body_volumes(seeds, volumes=mid, start_index=start_index)
        prompt = assemble_prompt(header, body, task)
        measured = count_tokens(prompt)
        delta = abs(measured - target_tokens)
        if delta < best_delta:
            best_delta = delta
            best_volumes = mid
        if measured < target_tokens * (1 - TOLERANCE):
            low = mid + 1
        elif measured > target_tokens * (1 + TOLERANCE):
            high = mid - 1
        else:
            return mid

    return best_volumes


def _estimate_single_pass_tokens(
    seeds: Sequence[Seed],
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
) -> int:
    body, _ = build_body_volumes(seeds, volumes=1, start_index=0)
    return count_tokens(assemble_prompt(header, body, task))


def select_with_volumes(
    seeds: Sequence[Seed],
    *,
    volumes: int,
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
    start_index: int,
) -> tuple[list[Seed], str, str, int]:
    body, used = build_body_volumes(seeds, volumes=volumes, start_index=start_index)
    prompt = assemble_prompt(header, body, task)
    measured = count_tokens(prompt)
    return used, prompt, task, measured


def calibrate_seed_subset_count(
    seeds: Sequence[Seed],
    *,
    target_tokens: int,
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
    start_index: int = 0,
) -> int:
    low, high = 1, len(seeds)
    best_count = 1
    best_delta = 10**9
    while low <= high:
        mid = (low + high) // 2
        ordered = rotate_seeds(seeds, start_index)[:mid]
        measured = count_tokens(assemble_prompt(header, build_body(ordered), task))
        delta = abs(measured - target_tokens)
        if delta < best_delta:
            best_delta = delta
            best_count = mid
        if measured < target_tokens * (1 - TOLERANCE):
            low = mid + 1
        elif measured > target_tokens * (1 + TOLERANCE):
            high = mid - 1
        else:
            return mid
    return best_count


def select_for_target(
    seeds: Sequence[Seed],
    *,
    target_tokens: int,
    count_tokens: Callable[[str], int],
    header: str,
    task: str,
    start_index: int,
) -> tuple[list[Seed], str, str, int, int]:
    """Return (seeds_used, prompt, task, measured, volumes_or_subset_count)."""
    single_pass = count_tokens(
        assemble_prompt(header, build_body(rotate_seeds(seeds, 0)), task)
    )
    if single_pass <= target_tokens * (1 + TOLERANCE):
        volumes = calibrate_volumes(
            seeds,
            target_tokens=target_tokens,
            count_tokens=count_tokens,
            header=header,
            task=task,
            start_index=start_index,
        )
        used, prompt, task, measured = select_with_volumes(
            seeds,
            volumes=volumes,
            count_tokens=count_tokens,
            header=header,
            task=task,
            start_index=start_index,
        )
        return used, prompt, task, measured, volumes

    count = calibrate_seed_subset_count(
        seeds,
        target_tokens=target_tokens,
        count_tokens=count_tokens,
        header=header,
        task=task,
        start_index=start_index,
    )
    ordered = rotate_seeds(seeds, start_index)[:count]
    body = build_body(ordered)
    prompt = assemble_prompt(header, body, task)
    measured = count_tokens(prompt)
    return ordered, prompt, task, measured, count
