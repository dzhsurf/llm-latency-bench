from __future__ import annotations

from scripts.seeds.types import Seed

CODING_NORMAL_TASKS = [
    (
        "For EACH module below, write a detailed review with these sections: "
        "(1) Purpose — what problem it solves; "
        "(2) Key Logic — quote 2-3 critical code lines verbatim and explain why they matter; "
        "(3) Usage Example — runnable snippet with expected output; "
        "(4) Edge Cases — at least 2 failure modes and how to handle them; "
        "(5) Reasoning — step-by-step walkthrough of the main algorithm. "
        "Do not skip any module. Aim for a thorough, publication-quality response."
    ),
    (
        "For EACH module below, perform a bug hunt: "
        "(1) Quote the suspicious code lines; "
        "(2) Explain the defect with concrete input that triggers it; "
        "(3) Provide the fixed code with reasoning for each change; "
        "(4) Write a minimal failing test and show it passing after the fix. "
        "Cover every module. Be exhaustive — quote source lines as evidence."
    ),
    (
        "For EACH module below, produce a refactoring report: "
        "(1) Quote current code that needs improvement; "
        "(2) Explain readability or type-safety issues with reasoning; "
        "(3) Show the refactored version with inline comments; "
        "(4) List what changed and why, citing original lines. "
        "Address all modules. Provide before/after comparisons."
    ),
    (
        "For EACH module below, design comprehensive unit tests: "
        "(1) Quote the public API signatures; "
        "(2) List edge cases with reasoning for why each matters; "
        "(3) Write test code for happy path, boundary, and error cases; "
        "(4) Explain expected assertions and failure messages. "
        "Cover every module. Include at least 3 test cases per module."
    ),
    (
        "For EACH module below, write API documentation: "
        "(1) Quote each public function/class signature; "
        "(2) Docstring with params, returns, raises, and complexity; "
        "(3) A design note explaining architectural choices with quoted evidence; "
        "(4) Integration example showing how modules work together. "
        "Document all modules fully. Cite source lines throughout."
    ),
]

CODING_STRUCTURED_TASKS = [
    (
        "Return ONLY valid JSON — a top-level array with one object per module below. "
        "Each object MUST have: "
        "name (string), purpose (string, 2+ sentences), "
        "key_logic_quote (verbatim code excerpt), key_logic_explanation (reasoning), "
        "complexity (time/space), params (array of {name, type, description}), "
        "returns (string), edge_cases (array of {scenario, handling}), "
        "suggested_test (string with test code). "
        "Include every module. No markdown fences."
    ),
    (
        "Return ONLY valid JSON — a top-level array with one object per module below. "
        "Each object MUST have: "
        "module_name (string), bug_location_quote (verbatim lines), "
        "bug_description (string), trigger_input (string), "
        "fix_reasoning (step-by-step string), fixed_code (string), "
        "test_code (string), test_expected_output (string). "
        "Cover every module. No markdown fences."
    ),
    (
        "Return ONLY valid JSON — a top-level array with one object per module below. "
        "Each object MUST have: "
        "module_name (string), issues (array of {quoted_code, problem, reasoning}), "
        "refactored_code (string), changes_summary (array of {before_quote, after, rationale}). "
        "Address all modules. No markdown fences."
    ),
    (
        "Return ONLY valid JSON — a top-level array with one object per module below. "
        "Each object MUST have: "
        "module_name (string), api_signatures (array of quoted strings), "
        "test_cases (array of {name, input, expected, reasoning, test_code}). "
        "At least 3 test cases per module. No markdown fences."
    ),
    (
        "Return ONLY valid JSON — a top-level array with one object per module below. "
        "Each object MUST have: "
        "module_name (string), public_api (array of {signature_quote, docstring, complexity}), "
        "design_rationale (string with quoted evidence), "
        "integration_example (string with code). "
        "Document every module. No markdown fences."
    ),
]

# Backward-compatible alias: normal cases 1-5, structured cases 6-10
CODING_TASKS = CODING_NORMAL_TASKS + CODING_STRUCTURED_TASKS

CODING_SEEDS: list[Seed] = [
    Seed(
        "rate_limiter_token_bucket",
        "Token Bucket Rate Limiter",
        '''```python
import time
from dataclasses import dataclass

@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float
    tokens: float = 0.0
    last_refill: float = 0.0

    def _refill(self, now: float) -> None:
        if self.last_refill == 0:
            self.last_refill = now
            self.tokens = self.capacity
            return
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        self._refill(now)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
```''',
    ),
    Seed(
        "retry_exponential_backoff",
        "Retry with Exponential Backoff",
        '''```python
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    base_delay: float = 0.2,
    jitter: float = 0.1,
) -> T:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == max_attempts - 1:
                break
            delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            time.sleep(delay)
    raise RuntimeError(f"failed after {max_attempts} attempts") from last_error
```''',
    ),
    Seed(
        "lru_cache",
        "LRU Cache",
        '''```python
from collections import OrderedDict
from typing import Any

class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
```''',
    ),
    Seed(
        "trie_autocomplete",
        "Trie Autocomplete",
        '''```python
from dataclasses import dataclass, field

@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    terminal: bool = False

class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.terminal = True

    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return []
            node = node.children[ch]
        results: list[str] = []
        self._dfs(node, prefix, results, limit)
        return results

    def _dfs(self, node: TrieNode, path: str, out: list[str], limit: int) -> None:
        if len(out) >= limit:
            return
        if node.terminal:
            out.append(path)
        for ch, child in sorted(node.children.items()):
            self._dfs(child, path + ch, out, limit)
```''',
    ),
    Seed(
        "graph_bfs",
        "Graph BFS Shortest Path",
        '''```python
from collections import deque
from typing import Hashable

def shortest_path(graph: dict[Hashable, list[Hashable]], start: Hashable, goal: Hashable) -> list[Hashable] | None:
    if start == goal:
        return [start]
    queue: deque[Hashable] = deque([start])
    parent: dict[Hashable, Hashable | None] = {start: None}
    while queue:
        node = queue.popleft()
        for nxt in graph.get(node, []):
            if nxt in parent:
                continue
            parent[nxt] = node
            if nxt == goal:
                path = [goal]
                cur = goal
                while parent[cur] is not None:
                    cur = parent[cur]
                    path.append(cur)
                return list(reversed(path))
            queue.append(nxt)
    return None
```''',
    ),
    Seed(
        "dijkstra",
        "Dijkstra Shortest Path",
        '''```python
import heapq
from typing import Hashable

def dijkstra(graph: dict[Hashable, list[tuple[Hashable, float]]], start: Hashable) -> dict[Hashable, float]:
    dist: dict[Hashable, float] = {start: 0.0}
    heap: list[tuple[float, Hashable]] = [(0.0, start)]
    while heap:
        cost, node = heapq.heappop(heap)
        if cost > dist.get(node, float("inf")):
            continue
        for nxt, weight in graph.get(node, []):
            new_cost = cost + weight
            if new_cost < dist.get(nxt, float("inf")):
                dist[nxt] = new_cost
                heapq.heappush(heap, (new_cost, nxt))
    return dist
```''',
    ),
    Seed(
        "json_path_extractor",
        "JSON Path Extractor",
        '''```python
from typing import Any

def extract_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if part.endswith("]"):
            key, idx_part = part[:-1].split("[")
            if key:
                current = current[key]
            index = int(idx_part)
            current = current[index]
        else:
            current = current[part]
    return current
```''',
    ),
    Seed(
        "csv_parser",
        "CSV Parser",
        '''```python
def parse_csv(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    row: list[str] = []
    cell: list[str] = []
    in_quotes = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    cell.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                cell.append(ch)
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ",":
                row.append("".join(cell))
                cell = []
            elif ch == "\n":
                row.append("".join(cell))
                rows.append(row)
                row, cell = [], []
            else:
                cell.append(ch)
        i += 1
    if cell or row:
        row.append("".join(cell))
        rows.append(row)
    return rows
```''',
    ),
    Seed(
        "state_machine",
        "Finite State Machine",
        '''```python
from dataclasses import dataclass
from typing import Callable, Hashable

@dataclass(frozen=True)
class Transition:
    event: Hashable
    target: Hashable

class StateMachine:
    def __init__(self, initial: Hashable) -> None:
        self.state = initial
        self._transitions: dict[tuple[Hashable, Hashable], Hashable] = {}
        self._on_enter: dict[Hashable, Callable[[], None]] = {}

    def add(self, source: Hashable, event: Hashable, target: Hashable) -> None:
        self._transitions[(source, event)] = target

    def on_enter(self, state: Hashable, handler: Callable[[], None]) -> None:
        self._on_enter[state] = handler

    def send(self, event: Hashable) -> Hashable:
        target = self._transitions[(self.state, event)]
        self.state = target
        handler = self._on_enter.get(target)
        if handler:
            handler()
        return self.state
```''',
    ),
    Seed(
        "connection_pool",
        "Connection Pool",
        '''```python
import queue
import threading
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

class ConnectionPool:
    def __init__(self, factory: Callable[[], T], max_size: int = 8) -> None:
        self._factory = factory
        self._pool: queue.Queue[T] = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created = 0
        self._max_size = max_size

    def _create(self) -> T:
        with self._lock:
            if self._created >= self._max_size:
                raise RuntimeError("pool exhausted")
            self._created += 1
        return self._factory()

    @contextmanager
    def acquire(self) -> Iterator[T]:
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            conn = self._create()
        try:
            yield conn
        finally:
            self._pool.put(conn)
```''',
    ),
    Seed(
        "event_bus",
        "In-Process Event Bus",
        '''```python
from collections import defaultdict
from typing import Any, Callable

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self._handlers[topic].append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        for handler in list(self._handlers.get(topic, [])):
            handler(payload)
```''',
    ),
    Seed(
        "min_heap",
        "Binary Min Heap",
        '''```python
class MinHeap:
    def __init__(self) -> None:
        self.data: list[int] = []

    def push(self, value: int) -> None:
        self.data.append(value)
        self._sift_up(len(self.data) - 1)

    def pop(self) -> int:
        if not self.data:
            raise IndexError("pop from empty heap")
        root = self.data[0]
        last = self.data.pop()
        if self.data:
            self.data[0] = last
            self._sift_down(0)
        return root

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if self.data[idx] >= self.data[parent]:
                break
            self.data[idx], self.data[parent] = self.data[parent], self.data[idx]
            idx = parent

    def _sift_down(self, idx: int) -> None:
        n = len(self.data)
        while True:
            left = 2 * idx + 1
            right = left + 1
            smallest = idx
            if left < n and self.data[left] < self.data[smallest]:
                smallest = left
            if right < n and self.data[right] < self.data[smallest]:
                smallest = right
            if smallest == idx:
                break
            self.data[idx], self.data[smallest] = self.data[smallest], self.data[idx]
            idx = smallest
```''',
    ),
    Seed(
        "union_find",
        "Union Find",
        '''```python
class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True
```''',
    ),
    Seed(
        "bloom_filter",
        "Bloom Filter",
        '''```python
import hashlib

class BloomFilter:
    def __init__(self, size: int, hashes: int = 3) -> None:
        self.size = size
        self.hashes = hashes
        self.bits = bytearray((size + 7) // 8)

    def _indexes(self, item: str) -> list[int]:
        out: list[int] = []
        for i in range(self.hashes):
            digest = hashlib.blake2b(f"{item}:{i}".encode(), digest_size=8).digest()
            out.append(int.from_bytes(digest, "big") % self.size)
        return out

    def add(self, item: str) -> None:
        for idx in self._indexes(item):
            self.bits[idx // 8] |= 1 << (idx % 8)

    def __contains__(self, item: str) -> bool:
        return all(self.bits[idx // 8] & (1 << (idx % 8)) for idx in self._indexes(item))
```''',
    ),
    Seed(
        "http_router",
        "Simple HTTP Router",
        '''```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class Request:
    method: str
    path: str

Handler = Callable[[Request], str]

class Router:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], Handler] = {}

    def route(self, method: str, path: str):
        def decorator(fn: Handler) -> Handler:
            self._routes[(method.upper(), path)] = fn
            return fn
        return decorator

    def dispatch(self, request: Request) -> str:
        handler = self._routes.get((request.method.upper(), request.path))
        if not handler:
            raise KeyError("route not found")
        return handler(request)
```''',
    ),
    Seed(
        "config_loader",
        "Layered Config Loader",
        '''```python
import json
from pathlib import Path
from typing import Any

class ConfigLoader:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self._cache: dict[str, Any] = {}

    def load(self, name: str) -> dict[str, Any]:
        if name in self._cache:
            return self._cache[name]
        path = self.base_path / f"{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        defaults = self.base_path / "defaults.json"
        if defaults.exists():
            base = json.loads(defaults.read_text(encoding="utf-8"))
            data = {**base, **data}
        self._cache[name] = data
        return data
```''',
    ),
    Seed(
        "task_scheduler",
        "Priority Task Scheduler",
        '''```python
import heapq
import time
from dataclasses import dataclass, field
from typing import Callable

@dataclass(order=True)
class ScheduledTask:
    run_at: float
    priority: int
    fn: Callable[[], None] = field(compare=False)

class Scheduler:
    def __init__(self) -> None:
        self._heap: list[ScheduledTask] = []

    def schedule(self, delay: float, fn: Callable[[], None], priority: int = 0) -> None:
        heapq.heappush(self._heap, ScheduledTask(time.monotonic() + delay, priority, fn))

    def run_ready(self) -> int:
        now = time.monotonic()
        executed = 0
        while self._heap and self._heap[0].run_at <= now:
            task = heapq.heappop(self._heap)
            task.fn()
            executed += 1
        return executed
```''',
    ),
    Seed(
        "markdown_table",
        "Markdown Table Builder",
        '''```python
def build_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    def fmt(cells: list[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)) + " |"
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    lines = [fmt(headers), sep]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)
```''',
    ),
    Seed(
        "sql_builder",
        "SQL Query Builder",
        '''```python
from dataclasses import dataclass

@dataclass
class Query:
    table: str
    columns: list[str]
    where: list[str]
    limit: int | None = None

    def to_sql(self) -> str:
        cols = ", ".join(self.columns) if self.columns else "*"
        sql = f"SELECT {cols} FROM {self.table}"
        if self.where:
            sql += " WHERE " + " AND ".join(self.where)
        if self.limit is not None:
            sql += f" LIMIT {self.limit}"
        return sql
```''',
    ),
    Seed(
        "ring_buffer",
        "Ring Buffer",
        '''```python
from typing import Generic, TypeVar

T = TypeVar("T")

class RingBuffer(Generic[T]):
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.buffer: list[T | None] = [None] * capacity
        self.head = 0
        self.size = 0

    def push(self, item: T) -> None:
        self.buffer[(self.head + self.size) % self.capacity] = item
        if self.size < self.capacity:
            self.size += 1
        else:
            self.head = (self.head + 1) % self.capacity

    def items(self) -> list[T]:
        return [self.buffer[(self.head + i) % self.capacity] for i in range(self.size)]
```''',
    ),
    Seed(
        "topological_sort",
        "Topological Sort",
        '''```python
from collections import deque
from typing import Hashable

def topological_sort(graph: dict[Hashable, list[Hashable]]) -> list[Hashable]:
    indegree: dict[Hashable, int] = {node: 0 for node in graph}
    for edges in graph.values():
        for nxt in edges:
            indegree[nxt] = indegree.get(nxt, 0) + 1
    queue = deque([n for n, d in indegree.items() if d == 0])
    order: list[Hashable] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in graph.get(node, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(indegree):
        raise ValueError("cycle detected")
    return order
```''',
    ),
    Seed(
        "memoize",
        "Memoization Decorator",
        '''```python
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

def memoize(fn: Callable[..., T]) -> Callable[..., T]:
    cache: dict[tuple, T] = {}

    @wraps(fn)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = fn(*args, **kwargs)
        return cache[key]

    return wrapper
```''',
    ),
    Seed(
        "async_batch",
        "Async Batch Processor",
        '''```python
import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")

async def map_in_batches(
    items: list[T],
    worker: Callable[[T], Awaitable[R]],
    batch_size: int = 16,
) -> list[R]:
    results: list[R] = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        chunk = await asyncio.gather(*(worker(item) for item in batch))
        results.extend(chunk)
    return results
```''',
    ),
    Seed(
        "log_parser",
        "Structured Log Parser",
        '''```python
import re
from dataclasses import dataclass
from datetime import datetime

LOG_RE = re.compile(
    r"^(?P<ts>\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}) (?P<level>\\w+) (?P<msg>.+)$"
)

@dataclass
class LogEntry:
    ts: datetime
    level: str
    message: str

def parse_logs(text: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for line in text.splitlines():
        match = LOG_RE.match(line.strip())
        if not match:
            continue
        entries.append(
            LogEntry(
                ts=datetime.fromisoformat(match.group("ts")),
                level=match.group("level"),
                message=match.group("msg"),
            )
        )
    return entries
```''',
    ),
    Seed(
        "feature_flags",
        "Feature Flag Evaluator",
        '''```python
import hashlib
from dataclasses import dataclass

@dataclass
class Flag:
    name: str
    enabled: bool
    rollout: float = 1.0

class FlagEvaluator:
    def __init__(self, flags: dict[str, Flag]) -> None:
        self.flags = flags

    def is_enabled(self, name: str, user_id: str) -> bool:
        flag = self.flags.get(name)
        if not flag or not flag.enabled:
            return False
        if flag.rollout >= 1.0:
            return True
        bucket = int(hashlib.md5(f"{name}:{user_id}".encode()).hexdigest(), 16) % 10000
        return bucket < int(flag.rollout * 10000)
```''',
    ),
    Seed(
        "diff_engine",
        "Line Diff Engine",
        '''```python
def diff_lines(old: list[str], new: list[str]) -> list[tuple[str, str]]:
    m, n = len(old), len(new)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if old[i] == new[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    i = j = 0
    out: list[tuple[str, str]] = []
    while i < m and j < n:
        if old[i] == new[j]:
            out.append(("=", old[i]))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            out.append(("-", old[i]))
            i += 1
        else:
            out.append(("+", new[j]))
            j += 1
    while i < m:
        out.append(("-", old[i]))
        i += 1
    while j < n:
        out.append(("+", new[j]))
        j += 1
    return out
```''',
    ),
    Seed(
        "password_strength",
        "Password Strength Checker",
        '''```python
import re

def password_strength(password: str) -> dict[str, bool | int]:
    return {
        "length_ok": len(password) >= 12,
        "has_lower": bool(re.search(r"[a-z]", password)),
        "has_upper": bool(re.search(r"[A-Z]", password)),
        "has_digit": bool(re.search(r"\\d", password)),
        "has_symbol": bool(re.search(r"[^A-Za-z0-9]", password)),
        "score": sum(
            [
                len(password) >= 12,
                bool(re.search(r"[a-z]", password)),
                bool(re.search(r"[A-Z]", password)),
                bool(re.search(r"\\d", password)),
                bool(re.search(r"[^A-Za-z0-9]", password)),
            ]
        ),
    }
```''',
    ),
    Seed(
        "template_renderer",
        "Mustache-Lite Template Renderer",
        '''```python
import re

TOKEN_RE = re.compile(r"{{\\s*(?P<name>\\w+)\\s*}}")

def render_template(template: str, context: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group("name")
        return context.get(key, "")
    return TOKEN_RE.sub(repl, template)
```''',
    ),
    Seed(
        "inventory_reservation",
        "Inventory Reservation Service",
        '''```python
from dataclasses import dataclass

@dataclass
class Reservation:
    sku: str
    qty: int

class InventoryService:
    def __init__(self, stock: dict[str, int]) -> None:
        self.stock = dict(stock)
        self.reserved: dict[str, int] = {}

    def reserve(self, sku: str, qty: int) -> Reservation:
        available = self.stock.get(sku, 0) - self.reserved.get(sku, 0)
        if qty > available:
            raise ValueError("insufficient stock")
        self.reserved[sku] = self.reserved.get(sku, 0) + qty
        return Reservation(sku=sku, qty=qty)

    def commit(self, reservation: Reservation) -> None:
        self.stock[reservation.sku] -= reservation.qty
        self.reserved[reservation.sku] -= reservation.qty
```''',
    ),
    Seed(
        "websocket_frame",
        "WebSocket Frame Parser",
        '''```python
from dataclasses import dataclass

@dataclass
class Frame:
    opcode: int
    payload: bytes

def parse_frame(data: bytes) -> Frame:
    if len(data) < 2:
        raise ValueError("frame too short")
    b1, b2 = data[0], data[1]
    opcode = b1 & 0x0F
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F
    offset = 2
    if length == 126:
        length = int.from_bytes(data[2:4], "big")
        offset = 4
    elif length == 127:
        length = int.from_bytes(data[2:10], "big")
        offset = 10
    mask = data[offset : offset + 4] if masked else b""
    offset += 4 if masked else 0
    payload = data[offset : offset + length]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return Frame(opcode=opcode, payload=payload)
```''',
    ),
    Seed(
        "metrics_histogram",
        "Latency Histogram",
        '''```python
from dataclasses import dataclass, field

@dataclass
class Histogram:
    buckets: list[float]
    counts: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.counts:
            self.counts = [0] * len(self.buckets)

    def observe(self, value: float) -> None:
        for i, upper in enumerate(self.buckets):
            if value <= upper:
                self.counts[i] += 1
                return
        self.counts[-1] += 1

    def percentile(self, p: float) -> float:
        total = sum(self.counts)
        if total == 0:
            return 0.0
        target = total * p
        running = 0
        for upper, count in zip(self.buckets, self.counts):
            running += count
            if running >= target:
                return upper
        return self.buckets[-1]
```''',
    ),
    Seed(
        "oauth_state",
        "OAuth State Manager",
        '''```python
import secrets
import time
from dataclasses import dataclass

@dataclass
class StateEntry:
    value: str
    expires_at: float

class OAuthStateStore:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl = ttl_seconds
        self._states: dict[str, StateEntry] = {}

    def issue(self) -> str:
        self._purge()
        value = secrets.token_urlsafe(24)
        self._states[value] = StateEntry(value=value, expires_at=time.time() + self.ttl)
        return value

    def consume(self, value: str) -> bool:
        self._purge()
        entry = self._states.pop(value, None)
        return entry is not None

    def _purge(self) -> None:
        now = time.time()
        expired = [k for k, v in self._states.items() if v.expires_at <= now]
        for key in expired:
            del self._states[key]
```''',
    ),
    Seed(
        "image_resize_plan",
        "Image Resize Planner",
        '''```python
from dataclasses import dataclass

@dataclass
class Size:
    width: int
    height: int

def plan_resize(src: Size, max_width: int, max_height: int) -> Size:
    ratio = min(max_width / src.width, max_height / src.height, 1.0)
    return Size(int(src.width * ratio), int(src.height * ratio))
```''',
    ),
    Seed(
        "git_semver",
        "Semantic Version Parser",
        '''```python
import re
from dataclasses import dataclass

SEMVER_RE = re.compile(
    r"^(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
)

@dataclass
class Version:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None

def parse_version(text: str) -> Version:
    match = SEMVER_RE.match(text)
    if not match:
        raise ValueError("invalid semver")
    return Version(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        match.group("prerelease"),
    )
```''',
    ),
    Seed(
        "markdown_toc",
        "Markdown TOC Generator",
        '''```python
import re

HEADING_RE = re.compile(r"^(?P<level>#{1,6})\\s+(?P<title>.+)$", re.MULTILINE)

def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

def build_toc(markdown: str) -> str:
    lines = ["# Table of Contents"]
    for match in HEADING_RE.finditer(markdown):
        level = len(match.group("level"))
        title = match.group("title").strip()
        indent = "  " * (level - 1)
        lines.append(f"{indent}- [{title}](#{slugify(title)})")
    return "\\n".join(lines)
```''',
    ),
    Seed(
        "cache_aside",
        "Cache-Aside Pattern",
        '''```python
from typing import Callable, TypeVar

T = TypeVar("T")

class CacheAside:
    def __init__(self, cache: dict[str, T]) -> None:
        self.cache = cache

    def get_or_load(self, key: str, loader: Callable[[], T]) -> T:
        if key in self.cache:
            return self.cache[key]
        value = loader()
        self.cache[key] = value
        return value
```''',
    ),
    Seed(
        "circuit_breaker",
        "Circuit Breaker",
        '''```python
import time
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar("T")

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = State.CLOSED
        self.opened_at = 0.0

    def call(self, fn: Callable[[], T]) -> T:
        if self.state == State.OPEN:
            if time.monotonic() - self.opened_at >= self.reset_timeout:
                self.state = State.HALF_OPEN
            else:
                raise RuntimeError("circuit open")
        try:
            result = fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = State.OPEN
                self.opened_at = time.monotonic()
            raise
        self.failures = 0
        self.state = State.CLOSED
        return result
```''',
    ),
    Seed(
        "saga_orchestrator",
        "Saga Orchestrator",
        '''```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class SagaStep:
    name: str
    action: Callable[[], None]
    compensate: Callable[[], None]

class Saga:
    def __init__(self, steps: list[SagaStep]) -> None:
        self.steps = steps

    def run(self) -> None:
        completed: list[SagaStep] = []
        try:
            for step in self.steps:
                step.action()
                completed.append(step)
        except Exception:
            for step in reversed(completed):
                step.compensate()
            raise
```''',
    ),
    Seed(
        "expression_eval",
        "Safe Arithmetic Expression Evaluator",
        '''```python
import ast
import operator as op

OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}

def eval_expr(expr: str) -> float:
    node = ast.parse(expr, mode="eval").body

    def _eval(n):
        if isinstance(n, ast.Num):
            return n.n
        if isinstance(n, ast.BinOp):
            return OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp):
            return OPS[type(n.op)](_eval(n.operand))
        raise ValueError("unsupported expression")

    return float(_eval(node))
```''',
    ),
    Seed(
        "idempotency_key",
        "Idempotency Key Store",
        '''```python
import time
from dataclasses import dataclass
from typing import Any

@dataclass
class Record:
    key: str
    response: Any
    expires_at: float

class IdempotencyStore:
    def __init__(self, ttl: float = 3600.0) -> None:
        self.ttl = ttl
        self._records: dict[str, Record] = {}

    def get(self, key: str) -> Any | None:
        self._purge()
        record = self._records.get(key)
        return None if record is None else record.response

    def put(self, key: str, response: Any) -> None:
        self._purge()
        self._records[key] = Record(key=key, response=response, expires_at=time.time() + self.ttl)

    def _purge(self) -> None:
        now = time.time()
        for key in [k for k, v in self._records.items() if v.expires_at <= now]:
            del self._records[key]
```''',
    ),
    Seed(
        "geo_hash",
        "Geohash Encoder",
        '''```python
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode_geohash(lat: float, lon: float, precision: int = 8) -> str:
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    even = True
    out: list[str] = []
    while len(out) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch |= bits[bit]
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= bits[bit]
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            out.append(BASE32[ch])
            bit = 0
            ch = 0
    return "".join(out)
```''',
    ),
]
