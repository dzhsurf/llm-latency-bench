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

```bash
python -m llm_bench --config config.yaml
```

Smoke a single case:

```bash
python -m llm_bench --config config.yaml --domain coding --length 1024
```

## Datasets

Static prompts live under `datasets/`. Each domain and context length has **10 distinct cases** (e.g. `coding/coding_1k_01.json` … `_10.json`), built from handwritten seed libraries in `scripts/seeds/`.

Regenerate datasets during development (combiner only — does not author content):

```bash
uv run python scripts/gen_datasets.py
```

The benchmark tool only reads `datasets/manifest.json` and prompt files at runtime.

## Output

- `results/raw_*.json` — per-request metrics
- `results/report_*.md` — aggregated tables
- Console summary via Rich

## Metrics

- **TTFT**: time to first streamed token (ms)
- **Decode TPS**: `(output_tokens - 1) / decode_duration`
- **Prefix cache**: miss uses unique metadata header; hit warms then reuses identical prefix
