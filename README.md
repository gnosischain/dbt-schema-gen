
![Schema Gen](img/header.png)

# dbt-schema-gen

Create and maintain rich `schema.yml` files for every model in your dbt
project – powered by the LLM of your choice  
(OpenAI, Anthropic Claude, Google Gemini, or any provider you bolt on).

---

## ✨ Key features

| Feature                       | Detail |
|-------------------------------|--------|
| **One-command run**           | `dbt-schema-gen </path/to/project | models/subfolder>` – works from the project root **or** any folder under `models/`. |
| **Selective generation**      | `-m / --models` flag regenerates just the models you’re working on. |
| **Smart overwrite**           | Skips models whose column list hasn’t changed; pass `-o / --overwrite` to force refresh. |
| **Test-less draft mode**      | `--skip-tests` drops every `tests:` block for ultra-fast rough drafts. |
| **Sector-aware prompting**    | Feeds the LLM the matching `{sector}_sources.yml` for richer context. |
| **dbt-utils alias fix-ups**   | LLM-invented tests (`equal`, `check_positive`, `between`, `regex_match` …) auto-rewrite to canonical `dbt_utils` tests. |
| **Pluggable provider layer**  | Swap OpenAI ↔ Anthropic ↔ Gemini (or your own) by flipping **one** env-var. |
| **Global rate-limiter**       | Token-bucket caps **all** API calls to `GLOBAL_MAX_RPM` (default 10). |
| **Automatic retries**         | Provider-aware back-off on 429 / quota errors, tunable via `*_MAX_RETRIES`. |
| **Editable install**          | `pip install -e .` for instant local hacking. |

---

## 🗂️ Project layout

```text
dbt-schema-gen/
├── pyproject.toml
├── requirements.txt
└── src/dbt_schema_gen/
    ├── cli.py               ← CLI & all post-processing logic
    ├── extractor.py         ← SQL & path parsing
    ├── renderer.py          ← Prompt builder
    ├── config.py            ← .env / env-var helper
    ├── utils/
    │   ├── __init__.py      ← public “barrel” re-exports
    │   ├── rate_limiter.py  ← global RPM bucket + retry decorator
    │   ├── pathing.py       ← locate models/ & yield *.sql
    │   ├── yaml_tools.py    ← sanitize / pretty-dump YAML
    │   └── tests.py         ← dbt_utils alias → canonical test mapper
    └── llm/
        ├── base.py
        ├── openai_provider.py
        ├── anthropic_provider.py
        └── gemini_provider.py
````

---

## ⚡ Quick start

```bash
# 1  clone & enter
git clone https://github.com/your-org/dbt-schema-gen.git
cd dbt-schema-gen

# 2  create venv & editable install
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 3  copy & edit credentials
cp .env.example .env          # paste your API key(s)

# 4a run from project root – scans *all* models
dbt-schema-gen /abs/path/to/my_dbt_project

# 4b run from deep folder – scans only that sub-tree
cd /my_dbt_project/models/execution/contracts/aave
dbt-schema-gen .

# 4c regenerate two models only, force overwrite, drop tests
dbt-schema-gen -m model_a,model_b -o --skip-tests /abs/path/to/my_dbt_project
```

CLI legend
`↗️ generated`  `⏭️ skipped (columns unchanged)`  `✅ file written`

---

## 🔧 Configuration

### Core variables

| Variable                                                  | Meaning                                             | Default          |
| --------------------------------------------------------- | --------------------------------------------------- | ---------------- |
| `LLM_PROVIDER`                                            | `openai` \| `anthropic` \| `gemini` \| `<your-own>` | `openai`         |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Provider API key                                    | –                |
| `OPENAI_MODEL`                                            | e.g. `gpt-4o-mini`, `gpt-3.5-turbo-0125`            | provider default |
| `ANTHROPIC_MODEL`                                         | e.g. `claude-3-opus-20240229`                       | provider default |
| `GEMINI_MODEL`                                            | `gemini-1.5-flash` \| `gemini-1.5-pro-latest`       | provider default |
| `*_TEMPERATURE`                                           | sampling temperature (`float`)                      | `0.3`            |

### Rate-limit & retry knobs

| Variable                | Purpose                             | Default |
| ----------------------- | ----------------------------------- | ------- |
| `GLOBAL_MAX_RPM`        | **Global** requests-per-minute cap  | `10`    |
| `OPENAI_MAX_RETRIES`    | extra attempts on 429 for OpenAI    | `3`     |
| `ANTHROPIC_MAX_RETRIES` | extra attempts on 429 for Anthropic | `3`     |
| `GEMINI_MAX_RETRIES`    | extra attempts on 429 for Gemini    | `1`     |

> **Tip**  Gemini Flash free tier allows **10 RPM** – the defaults are safe.

---

## 🗺️ How it works

1. **Locate models root** – supports project root or nested folder calls.
2. **Walk** matching `*.sql` files (optionally filtered by `-m`).
3. **Skip** models whose column names haven’t changed (unless `-o`).
4. **Build prompt** with SQL, column list, and `{sector}_sources.yml`.
5. **LLM → YAML → sanitise**; rewrite test aliases to canonical `dbt_utils`.
6. **Merge / write** one `schema.yml` per directory.

---

## 💬 Supported providers

| Provider      | File                     | Notes                                           |
| ------------- | ------------------------ | ----------------------------------------------- |
| **OpenAI**    | `openai_provider.py`     | ChatCompletion v1; retries + global limiter     |
| **Anthropic** | `anthropic_provider.py`  | Claude 3; same interface                        |
| **Gemini**    | `gemini_provider.py`     | Uses `google-generativeai`; honours retry hints |
| **Custom**    | `llm/<name>_provider.py` | Sub-class `LLMProvider`, implement `generate()` |

Switch providers:

```bash
LLM_PROVIDER=gemini \
GEMINI_API_KEY=AIza... \
GLOBAL_MAX_RPM=10 \
dbt-schema-gen .
```

---

## License

[MIT](LICENSE)

