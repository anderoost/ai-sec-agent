# ai-sec-agent

Local security assessment agent for Draw.io and PDF architecture diagrams.

## What it does

- Parses `.drawio` / `.xml` architecture diagrams and PDF diagrams.
- Uses a local open-source model to evaluate the architecture against Irius Risk-style threat modeling.
- Estimates coverage for CIS Critical Security Controls in:
  - Application Software Security
  - Data Protection
- Emits a Markdown or PDF security assessment report.

## Recommended local model

The agent is designed to run locally with an open-source model such as a quantized Llama 2 chat model (for example `llama-2-7b-chat.gguf`) via `llama-cpp-python`.

## Setup

Install the dependencies:

```bash
python3 -m pip install -r requirements.txt
```

If you want fallback support with Hugging Face transformers, also install:

```bash
python3 -m pip install transformers torch
```

## Usage

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
  --model-path /path/to/llama-2-7b-chat.gguf \
  --ocr
```

### Optional Irius Risk API integration

If you have a free Irius Risk API endpoint and API key, pass them as:

```bash
python agent.py \
  --input architecture.drawio \
  --output report.md \
  --model-path /path/to/llama-2-7b-chat.gguf \
  --irius-api-url https://app.iriusrisk.com \
  --irius-api-key YOUR_API_KEY
```

## Output

The report includes:

- Irius Risk threat counts by severity: Critical, High, Medium, Low
- CIS coverage estimates for Application Software Security and Data Protection
- Local threat examples and analysis notes
- Raw model output for review
