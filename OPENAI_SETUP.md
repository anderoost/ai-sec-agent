# OpenAI Integration Setup Guide

## Configuration

A `.env` file has been created in the project root. Edit it and add your OpenAI API key:

```
OPENAI_API_KEY=your_actual_openai_api_key
OPENAI_MODEL=gpt-4o-mini
DEBUG=false
```

**Note:** The `.env` file is already in `.gitignore` to protect your credentials.

## Installation

Install the new dependencies:

```bash
pip install -r requirements.txt
```

Key additions:
- `openai>=1.0.0` - OpenAI Python client
- `python-dotenv>=1.0.0` - Environment variable loader
- `pytm>=0.9.0` - OWASP threat modeling (now in requirements)

## Usage

### Using OpenAI API (Recommended)

Once you've set your `OPENAI_API_KEY` in `.env`:

```powershell
py agent.py --input sample.drawio --output report.md
```

The tool will automatically:
1. Load your OpenAI API key from `.env`
2. Use GPT-4o-mini (or your configured model) for threat assessment
3. Analyze against CIS Critical Security Controls
4. Include pytm threat modeling results
5. Generate a comprehensive markdown report

### Using Local Model (Fallback)

If `OPENAI_API_KEY` is not set or the API call fails:

```powershell
py agent.py --input sample.drawio --output report.md --model-path "C:\path\to\local\model"
```

### Using Mock Mode (Testing)

```powershell
py agent.py --input sample.drawio --output report.md --model-path mock
```

## Report Contents

The generated report includes:

- **Severity Summary**: Critical/High/Medium/Low threat counts
- **CIS Coverage Estimates**: Coverage % for 6 key CIS controls with safeguard references
- **Threat Examples**: Security issues mapped to CIS controls
- **Pytm Analysis**: Automated threat modeling results (if available)
- **Raw LLM Output**: Full model response for transparency

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `OPENAI_MODEL` | gpt-4o-mini | OpenAI model to use (gpt-4, gpt-4-turbo, etc.) |
| `DEBUG` | false | Enable debug logging |

## Troubleshooting

**"No such file or directory: '.env'"**
- The .env file is already created. Make sure you're in the project directory.

**"Cannot access gated repo..."**
- This is expected if you were trying to use Gemma-3. OpenAI API is now the primary method.

**"Falling back to local model..."**
- Your OpenAI API key may be invalid or the API is unreachable. Check your key and internet connection.

**"ModuleNotFoundError: No module named 'openai'"**
- Run `pip install -r requirements.txt` to install dependencies.

## Cost Estimation

Using gpt-4o-mini:
- ~500 tokens per architecture analysis
- Typical cost: ~$0.0005 per report
- Check OpenAI pricing for your region
