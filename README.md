![Schema Gen](img/header.png)

# dbt-schema-gen

Automate the creation of rich `schema.yml` files for every model in your dbt
project, powered by the LLM of your choice (OpenAI, Anthropic Claude, Google
Gemini — or any provider you bolt on).

---

## ✨  Key features

| Feature | Detail |
|---------|--------|
| **Zero-config walk-through** | Scans every `models/**/*.sql` file, no model-by-model boilerplate. |
| **Sector-aware** | Feeds the LLM the matching `{sector}_sources.yml` for richer context. |
| **Pluggable provider layer** | Switch between OpenAI, Anthropic, Gemini (or your own) by flipping **one** environment variable. |
| **Global rate-limiter** | A token-bucket caps **all** API calls to `GLOBAL_MAX_RPM` (default 10) – perfect for limited Gemini Flash quotas. |
| **Automatic retries** | Provider-aware back-off on 429 / quota errors, tunable via `*_MAX_RETRIES`. |
| **Editable install** | `pip install -e .` for instant local hacking. |
| **CLI first** | `dbt-schema-gen /path/to/dbt/project` refreshes every `schema.yml` in seconds. |

---

## 🗂️  Project layout

```text
dbt-schema-gen/
├── pyproject.toml
├── requirements.txt
└── src/dbt_schema_gen/
    ├── cli.py            ← Click command
    ├── extractor.py      ← SQL & path parsing
    ├── renderer.py       ← Prompt builder
    ├── utils.py          ← global RPM limiter + retry decorator
    ├── config.py         ← .env / env-var helper
    └── llm/
        ├── base.py
        ├── openai_provider.py
        ├── anthropic_provider.py
        └── gemini_provider.py
````

---

## ⚡  Quick start

```bash
# 1  clone & enter
git clone https://github.com/your-org/dbt-schema-gen.git
cd dbt-schema-gen

# 2  create venv & editable install
python -m venv .venv && source .venv/bin/activate
pip install -e .        # pulls deps from pyproject / requirements

# 3  copy & edit .env
cp .env.example .env     # then paste your API key(s)

# 4  run against a dbt repo
dbt-schema-gen /absolute/path/to/my_dbt_project
```

Console output:

```
↗️  generating schema for models/ESG/metrics/esg_carbon_emissions.sql
✅  wrote models/ESG/metrics/schema.yml
…
All done! 🎉
```

---

## 🔧  Configuration

### Core variables

| Variable                                                  | Meaning                                             | Default          |
| --------------------------------------------------------- | --------------------------------------------------- | ---------------- |
| `LLM_PROVIDER`                                            | `openai` \| `anthropic` \| `gemini` \| `<your-own>` | `openai`         |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | API key for chosen provider                         | —                |
| `OPENAI_MODEL`                                            | e.g. `gpt-4o-mini`, `gpt-3.5-turbo-0125`            | provider default |
| `ANTHROPIC_MODEL`                                         | e.g. `claude-3-opus-20240229`                       | provider default |
| `GEMINI_MODEL`                                            | `gemini-1.5-flash` \| `gemini-1.5-pro-latest`       | provider default |
| `*_TEMPERATURE`                                           | sampling temperature (`float`)                      | `0.3`            |

### Rate-limit & retry knobs

| Variable                | Purpose                                                          | Default |
| ----------------------- | ---------------------------------------------------------------- | ------- |
| `GLOBAL_MAX_RPM`        | **Global** hard-cap across *all* providers (requests per minute) | `10`    |
| `OPENAI_MAX_RETRIES`    | extra attempts on 429 for OpenAI                                 | `3`     |
| `ANTHROPIC_MAX_RETRIES` | extra attempts on 429 for Anthropic                              | `3`     |
| `GEMINI_MAX_RETRIES`    | extra attempts on 429 for Gemini                                 | `1`     |

> **Tip:** Gemini Flash free tier allows **10 RPM**, so the defaults are safe
> out-of-the-box.

---

## 💬  Supported providers

| Provider  | File                                                  | Notes                                                                          |
| --------- | ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| OpenAI    | `openai_provider.py`                                  | ChatCompletion v1, unified retry decorator.                                    |
| Anthropic | `anthropic_provider.py`                               | Claude 3, unified retry decorator.                                             |
| Gemini    | `gemini_provider.py`                                  | `google-generativeai`; handles `retry_delay` hints.                            |
| Custom    | *(write)* `src/dbt_schema_gen/llm/<name>_provider.py` | Sub-class `LLMProvider` and decorate `generate()` with `@retry_on_rate_limit`. |

Switching providers:

```bash
LLM_PROVIDER=gemini \
GEMINI_API_KEY=AIza... \
GLOBAL_MAX_RPM=10 \
dbt-schema-gen /path/to/project
```

---

## 🗺️  How it works

1. **Walk** `models/**/*.sql`.
2. **Extract** model-level metadata & column hints.
3. **Find** `{sector}_sources.yml` for extra context.
4. **Prompt** the LLM.
5. **Sanitise + validate** the YAML reply.
6. **Write / update** one `schema.yml` per directory.

---


## License

[MIT](LICENSE)


