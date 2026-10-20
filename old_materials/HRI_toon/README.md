# HRI_toon

Demos of **TOON** (Token-Oriented Object Notation), a compact alternative to JSON for sending structured data to LLMs. TOON writes field names once per array instead of repeating them for every record, so it uses fewer tokens.

The demos use a sample dataset of 20 fake employees and a local [Ollama](https://ollama.com) model. No API keys are needed.

## Files

| File | What it does |
|------|--------------|
| `test.json` | Sample data: `employees` array with 20 records (id, name, email, department, position, salary, years of experience, active flag, hire date, phone). |
| `output.toon` | TOON version of `test.json`, written by `convert.js`. Starts with the header `employees[20]{id,firstName,...}:` followed by one comma-separated row per employee. |
| `convert.js` | Reads `test.json`, encodes it with `@toon-format/toon`, writes `output.toon`, and prints the character count for JSON vs. TOON and the percentage saved. |
| `test.py` | Python version of the same idea (uses the `toon_format` package). Prints the JSON and TOON forms, compares characters, estimates tokens (about 4 characters per token) and cost (at $0.003 per 1K tokens), and scales the saving to 1000 calls a day. Writes `test_toon.txt`. |
| `query-data.js` | Chat with the employee data. Encodes `test.json` as TOON, puts it in a system prompt, and asks a local Ollama model (default `gemma3:4b`) your question. Pass the question as an argument for a single answer, or run with no arguments for an interactive loop (`exit` or `quit` to leave). It has a list of example questions (headcount, average salary, recent hires), but `main()` does not call `runExampleQueries`. |
| `ollama-integration.js` | Five examples using the Ollama HTTP API (`localhost:11434`, default model `llama3.2`): (1) send TOON as input, (2) ask the model to reply in TOON, (3) tab-delimited TOON for fewer tokens, (4) validate TOON with `decode(..., { strict: true })`, (5) full workflow of encode, send, extract the code block, and validate. |
| `package.json` | Node project (ES modules). Dependencies: `@toon-format/toon` and `ollama`. |

## Setup

```bash
cd old_materials/HRI_toon
npm install
```

For the Ollama demos, install Ollama, start it (`ollama serve`) and pull the models:

```bash
ollama pull llama3.2
ollama pull gemma3:4b
```

For `test.py`:

```bash
pip install toon-format
```

## Usage

```bash
node convert.js                                   # JSON -> TOON, prints the size comparison
python3 test.py                                   # same, with token and cost estimates
node query-data.js "Who are the highest paid employees?"
node query-data.js                                # interactive mode
node ollama-integration.js                        # runs all five examples
```

## Notes

- Run every command from inside this folder. The scripts read `test.json` with a relative path.
- The data is made up. The names, emails and phone numbers are not real.
- `ollama-integration.js` always runs all five examples, and the model's TOON output is not guaranteed to be valid. That is the reason for the strict-mode validation step.
- Small local models can get calculations wrong (for example an average salary), so check answers from `query-data.js` against the data.
