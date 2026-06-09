# LLM API Performance Benchmark Tool

Benchmark any deployed LLM API endpoint (OpenAI-compatible or Anthropic-compatible) for:

- TTFT across input context sizes (1k–128k)
- Decode TPS
- Prefix caching hit vs miss TTFT comparison
- Serial latency and optional concurrent throughput

## Setup

Uses [uv](https://docs.astral.sh/uv/) for the virtual environment and dependencies:

```bash
uv venv
uv pip install -r requirements.txt
```

Activate the venv when needed (Cursor may do this automatically if `.venv` is detected):

```bash
source .venv/bin/activate
```

Or run commands without activating:

```bash
uv run python -m llm_bench --config config.yaml
```

## Configure

Edit `config.yaml`:

- **OpenAI-compatible**: `base_url: http://127.0.0.1:7575/v1`, `api_type: openai`
- **Anthropic-compatible**: `base_url: http://127.0.0.1:7575`, `api_type: anthropic`

Secrets can reference environment variables in the YAML, e.g. `api_key: "$GLM_API_KEY"`.
On startup the tool loads `.env` from the project root (or next to the config file) if it
exists; those values override the current shell environment. If `.env` is missing, only
already-exported environment variables are used.

## Run

Each run creates a **session** under `results/{session_id}/` (id format: `YYYYMMDD-xxxxxxxx`).
Progress is checkpointed after every completed case (warmup + all repeats). You can stop
with Ctrl+C after the current case finishes and resume later.

```bash
python -m llm_bench --config config.yaml
# Session: 20260609-a3f8c2e1  →  results/20260609-a3f8c2e1/
```

Resume a session:

```bash
python -m llm_bench --config config.yaml --resume 20260609-a3f8c2e1
```

Optional explicit session id for a new run:

```bash
python -m llm_bench --config config.yaml --session my-local-run-01
```

Smoke a single case:

```bash
python -m llm_bench --config config.yaml --domain coding --length 1024
```

`--resume` cannot be combined with `--domain` or `--length`.

## Datasets

Static prompts live under `datasets/`. Each domain and context length has **10 distinct cases** (e.g. `coding/coding_1k_01.json` … `_10.json`), built from handwritten seed libraries in `tools/seeds/`.

Regenerate datasets during development (combiner only — does not author content):

```bash
uv run python tools/gen_datasets.py
```

The benchmark tool only reads `datasets/manifest.json` and prompt files at runtime.

## Output

Per session (`results/{session_id}/`):

| File | Description |
|------|-------------|
| `meta.json` | Config snapshot, planned workload, fingerprint |
| `checkpoint.json` | Completed units and progress |
| `records.jsonl` | Append-only per-unit metrics |
| `report.md` | Aggregated tables (updated after each case) |
| `raw.json` | Full export written when the session completes |

Console summary via Rich prints on completion.

## Metrics

- **TTFT**: time to first streamed token (ms)
- **Decode TPS**: `(output_tokens - 1) / decode_duration`
- **Prefix cache**: miss uses unique metadata header; hit warms then reuses identical prefix
