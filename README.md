![Schema Gen](img/header.png)

# dbt-schema-gen

Automate the creation of rich `schema.yml` files for every model in your dbt
project, using the LLM of your choice (OpenAI, Anthropic Claude, Google Gemini,
or any custom provider you add).

---

## ✨ Key features

* **Zero-config walk-through** – scans every `models/**/*.sql` file.
* **Sector-aware** – pulls `{sector}_sources.yml` to give the LLM maximum
  context.
* **Pluggable provider layer** – swap between OpenAI, Anthropic, Gemini, or
  your own wrapper by changing **one** environment variable.
* **Editable install** – `pip install -e .` for instant local development.
* **CLI first** – `dbt-schema-gen /path/to/dbt/project` generates / refreshes
  all `schema.yml` files in seconds.

---

## 🗂️ Project layout

```

dbt-schema-gen/
├── pyproject.toml
├── requirements.txt
└── src/dbt_schema_gen/
    ├── cli.py            ← Click command
    ├── extractor.py      ← SQL + path parsing
    ├── renderer.py       ← Prompt builder
    ├── config.py         ← .env / env-var helper
    └── llm/
        ├── base.py
        ├── openai_provider.py
        ├── anthropic_provider.py
        └── gemini_provider.py

````

---

## ⚡ Quick start

```bash
# 1  Clone the repo and enter it
git clone https://github.com/your-org/dbt-schema-gen.git
cd dbt-schema-gen

# 2  Create a virtualenv and install in editable mode
python -m venv .venv && source .venv/bin/activate
pip install -e .                     # pulls deps from pyproject / requirements

# 3  Add your LLM credentials
cat > .env <<'EOF'
# choose ONE provider ↓↓↓
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini     # optional
OPENAI_TEMPERATURE=0.3       # optional
EOF

# 4  Run against a dbt repo (can be anywhere)
dbt-schema-gen /absolute/path/to/my_dbt_project
````

You’ll see log lines like:

```
✅  wrote models/execution/schema.yml
✅  wrote models/marts/core/schema.yml
All done! 🎉
```

---

## 🔧 Configuration

All options are driven by environment variables (directly or via `.env`).

| Variable                                                  | Meaning                                       | Default          |
| --------------------------------------------------------- | --------------------------------------------- | ---------------- |
| `LLM_PROVIDER`                                            | `openai`, `anthropic`, `gemini`, `<your-own>` | `openai`         |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | API key for the chosen provider               | —                |
| `OPENAI_MODEL`                                            | e.g. `gpt-4o-mini` \| `gpt-3.5-turbo-0125`    | provider default |
| `ANTHROPIC_MODEL`                                         | `claude-3-opus-20240229`                      | provider default |
| `GEMINI_MODEL`                                            | `gemini-1.5-pro-latest`                       | provider default |
| `*_TEMPERATURE`                                           | sampling temperature (`float`)                | `0.3`            |

---

## 💬 Supported providers

| Provider          | File                                                | Notes                                                                 |
| ----------------- | --------------------------------------------------- | --------------------------------------------------------------------- |
| **OpenAI**        | `openai_provider.py`                                | ChatCompletion v1; retries & YAML validation.                         |
| **Anthropic**     | `anthropic_provider.py`                             | Works with Claude 3; same interface.                                  |
| **Google Gemini** | `gemini_provider.py`                                | Uses `google-generativeai`; no system role (folded into user prompt). |
| **Custom**        | *write* `src/dbt_schema_gen/llm/<name>_provider.py` | Sub-class `LLMProvider` and implement `generate(prompt)`.             |

Switching providers:

```bash
LLM_PROVIDER=gemini  GEMINI_API_KEY=AIza...  dbt-schema-gen /path/to/project
```

---

## 🗺️ How it works

1. **Walk** `models/**/*.sql`.
2. **Extract**

   * model name, sector, tags
   * column list from `SELECT` (best-effort)
   * inline `-- @column col: desc` comments
3. **Find** the sector’s `{sector}_sources.yml` (if any).
4. **Build** a structured prompt and feed it to the LLM.
5. **Validate** the YAML returned; write `schema.yml` beside the model.

---

## 🛠️ Development

```bash
# lint + format
ruff check src
black src

# tests (if/when you add them)
pytest
```

---

## License

This project is licensed under the [MIT License](LICENSE).


