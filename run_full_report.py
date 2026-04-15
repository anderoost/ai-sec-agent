from pathlib import Path
import subprocess
import json
from agent import (
    build_architecture_summary,
    format_assessment_prompt,
    parse_counts_and_percentages,
    build_report_markdown,
    run_pytm_model,
)

MODEL = "gemma3:270M"
INPUT = Path("sample.drawio")
OUTPUT = Path("report_with_pytm_final.md")

arch = build_architecture_summary(INPUT)
# run pytm
pytm_threats = run_pytm_model(INPUT)

prompt = format_assessment_prompt(arch)

# Direct Ollama invocation
cmd = ["ollama", "run", MODEL, prompt, "--format", "json"]
proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
if proc.returncode != 0:
    print("OLLAMA ERROR:", proc.stderr)
    raise SystemExit(1)

llm_output = None
try:
    j = json.loads(proc.stdout)
    if isinstance(j, dict) and "response" in j:
        llm_output = j["response"].strip()
    elif isinstance(j, dict) and "output" in j:
        llm_output = j["output"].strip()
    elif isinstance(j, dict) and "choices" in j:
        llm_output = "\n".join([c.get("content", "") for c in j["choices"]])
    else:
        llm_output = proc.stdout
except Exception:
    llm_output = proc.stdout

parsed = parse_counts_and_percentages(llm_output)
if pytm_threats:
    parsed.setdefault('threat_examples', [])
    parsed['threat_examples'].extend([f"[pytm] {t}" for t in pytm_threats])

report = build_report_markdown(INPUT, arch, llm_output, parsed)
OUTPUT.write_text(report, encoding='utf-8')
print(f"Wrote: {OUTPUT}")
