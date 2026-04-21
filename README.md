# ai-sec-agent

Local security assessment agent for Draw.io and PDF architecture diagrams.

## What it does

- Parses `.drawio` / `.xml` architecture diagrams and PDF diagrams.
 - Uses a local open-source model to evaluate the architecture against the CIS Critical Security Controls (local LLM-driven assessment).
- Estimates coverage for CIS Critical Security Controls in:
  - Application Software Security
  - Data Protection
- Emits a Markdown or PDF security assessment report.

## Recommended local model

The agent defaults to and is tested with the Gemma 3 270M model (`gemma3-270m`). Gemma models work well via the Hugging Face `transformers` pipeline (no native C build required).

If you prefer to run Llama-family models via `llama-cpp-python`, see the Troubleshooting section below for Windows-specific installation notes.

## Setup

Install the dependencies:

```bash
python3 -m pip install -r requirements.txt
```

This will install the core runtime dependencies. The project now defaults to using `gemma3-270m` via `transformers` so `transformers` and `torch` are included in `requirements.txt`.

Optional: if you want native `llama-cpp-python` support (for gguf/llama models), install it separately — see Troubleshooting below for Windows.

## Usage

```bash
python agent.py \
  --input architecture.drawio \
  --output report.md
```

By default the agent will use `gemma3-270m`. To override and point at a different local model (gguf or a transformers identifier), pass `--model-path`:

```bash
python agent.py \
  --input architecture.drawio \
  --output report.md \
  --model-path /path/to/llama-2-7b-chat.gguf
```

For PDF inputs with image-based diagrams, enable OCR:

```bash
python agent.py \
  --input architecture.pdf \
  --output report.pdf \
  --ocr
```

## Discord Bot Integration

The agent can also run as a Discord bot for interactive security assessments and Q&A.

### Setup

1. Follow the [Discord Bot Setup Instructions](DISCORD_SETUP.md)
2. Install additional dependencies:
   ```bash
   pip install discord.py
   ```

### Running the Bot

```bash
python discord_bot.py
```

### Bot Features

**Security Assessments:**
- Upload Draw.io files to any channel for automated analysis
- Receives comprehensive security reports with threat modeling

**Security Q&A:**
- Ask general security questions via mentions or DMs
- Examples:
  - `@Bot What WAF tools do you recommend for AWS?`
  - `@Bot How to secure AI applications?`
  - `@Bot Best practices for API security`

## Output

The report includes:

- Severity counts by threat level: Critical, High, Medium, Low
- CIS coverage estimates for the following controls:
  - Data Protection
  - Account Management
  - Access Control Management
  - Audit Log Management
  - Network Monitoring and Defense
  - Application Software Security
- Local threat examples and analysis notes (mapped to CIS controls)
- Raw model output for review

## Troubleshooting: Windows and `llama-cpp-python`

If `pip install llama-cpp-python` fails with "Failed to build installable wheels for some pyproject.toml based projects", it's usually because a native C/C++ build is required and build tools are missing. Options:

- Preferred (easy): use the `transformers` + `torch` path with `gemma3-270m` (no native build required). The project defaults to `gemma3-270m` so no extra steps are needed.

- If you need `llama-cpp-python` (gguf native backend), try one of the following:

  1. Upgrade packaging tools and retry:

  ```bash
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install llama-cpp-python
  ```

  2. Install required native build tools (Windows):

  - Install "Build Tools for Visual Studio" (C++), CMake, and optionally Ninja. Then retry the `pip` install.

  3. Use Conda (often provides prebuilt binaries):

  ```bash
  conda install -c conda-forge llama-cpp-python
  ```

  4. Use WSL (Windows Subsystem for Linux) or a Linux/macOS environment where prebuilt wheels are more commonly available.

If you're still stuck, run the failing `pip` command and share the full error output; the log usually indicates which C/C++ dependency is missing.
