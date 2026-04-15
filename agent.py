#!/usr/bin/env python3
"""Local security assessment agent for Draw.io and PDF architecture diagrams."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from the script directory
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def parse_drawio(file_path: Path) -> str:
    raw = file_path.read_bytes()
    xml_text = None
    stripped = raw.lstrip()

    if stripped.startswith(b"<"):
        xml_text = raw.decode("utf-8", errors="ignore")
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    if name.endswith((".drawio", ".xml", ".txt")):
                        xml_text = archive.read(name).decode("utf-8", errors="ignore")
                        break
        except zipfile.BadZipFile:
            try:
                xml_text = gzip.decompress(raw).decode("utf-8", errors="ignore")
            except OSError:
                xml_text = raw.decode("utf-8", errors="ignore")

    if xml_text is None or not xml_text.strip():
        raise ValueError("Unable to parse Draw.io input. The file may be corrupted or unsupported.")

    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
    except Exception as exc:
        raise ValueError(f"Unable to parse Draw.io XML: {exc}") from exc

    nodes: List[Dict[str, str]] = []
    edges: List[Dict[str, str]] = []
    id_map: Dict[str, Dict[str, str]] = {}

    for cell in root.findall('.//mxCell'):
        cell_id = cell.get('id', '')
        value = (cell.get('value') or '').strip()
        edge = cell.get('edge') == '1'
        vertex = cell.get('vertex') == '1'
        style = cell.get('style', '')

        if vertex or (value and not edge):
            node = {'id': cell_id, 'label': value or '<unnamed>', 'style': style}
            nodes.append(node)
            if cell_id:
                id_map[cell_id] = node

        if edge:
            edges.append(
                {
                    'id': cell_id,
                    'source': cell.get('source', ''),
                    'target': cell.get('target', ''),
                    'label': value,
                    'style': style,
                }
            )

    summary = [f"Draw.io architecture analysis for {file_path.name}", ""]

    if nodes:
        summary.append("Components:")
        for node in nodes:
            summary.append(f"- {node['label']}")
    else:
        summary.append("Components: none detected from Draw.io nodes.")

    if edges:
        summary.append("")
        summary.append("Connections:")
        for edge in edges:
            source_label = id_map.get(edge['source'], {}).get('label', '<unknown>')
            target_label = id_map.get(edge['target'], {}).get('label', '<unknown>')
            label = f" ({edge['label']})" if edge['label'] else ""
            summary.append(f"- {source_label} -> {target_label}{label}")
    else:
        summary.append("")
        summary.append("Connections: no explicit edges detected.")

    return "\n".join(summary)


def parse_drawio_struct(file_path: Path) -> Dict[str, Any]:
    """Return structured nodes and edges from a Draw.io file for programmatic use."""
    raw = file_path.read_bytes()
    xml_text = None
    stripped = raw.lstrip()

    if stripped.startswith(b"<"):
        xml_text = raw.decode("utf-8", errors="ignore")
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    if name.endswith((".drawio", ".xml", ".txt")):
                        xml_text = archive.read(name).decode("utf-8", errors="ignore")
                        break
        except zipfile.BadZipFile:
            try:
                xml_text = gzip.decompress(raw).decode("utf-8", errors="ignore")
            except OSError:
                xml_text = raw.decode("utf-8", errors="ignore")

    if xml_text is None or not xml_text.strip():
        raise ValueError("Unable to parse Draw.io input for structure extraction.")

    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
    except Exception as exc:
        raise ValueError(f"Unable to parse Draw.io XML: {exc}") from exc

    nodes: List[Dict[str, str]] = []
    edges: List[Dict[str, str]] = []

    for cell in root.findall('.//mxCell'):
        cell_id = cell.get('id', '')
        value = (cell.get('value') or '').strip()
        edge = cell.get('edge') == '1'
        vertex = cell.get('vertex') == '1'

        if vertex or (value and not edge):
            node = {'id': cell_id, 'label': value or '<unnamed>'}
            nodes.append(node)

        if edge:
            edges.append(
                {
                    'id': cell_id,
                    'source': cell.get('source', ''),
                    'target': cell.get('target', ''),
                    'label': value,
                }
            )

    return {'nodes': nodes, 'edges': edges}


def parse_pdf(file_path: Path, use_ocr: bool = False) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("PyMuPDF is required to parse PDF diagrams. Install it via pip.") from exc

    document = fitz.open(file_path)
    pages: List[str] = []

    for page_index, page in enumerate(document, start=1):
        raw_text = page.get_text("text")
        if raw_text.strip():
            pages.append(f"--- Page {page_index} ---\n{raw_text.strip()}")
            continue

        if use_ocr:
            ocr_text = ocr_pdf_page(page)
            if ocr_text.strip():
                pages.append(f"--- Page {page_index} (OCR) ---\n{ocr_text.strip()}")

    if not pages:
        fallback = [page.get_text("blocks") for page in document]
        pages = [f"--- Page {i+1} ---\n{page}" for i, page in enumerate(fallback) if page.strip()]

    if not pages:
        raise ValueError("Unable to extract text from PDF. The diagram may be image-based and OCR may be required.")

    return "\n\n".join(pages)


def ocr_pdf_page(page: Any) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError("Pillow is required for OCR on PDF images.") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ImportError("pytesseract is required for OCR on PDF images.") from exc

    text_chunks: List[str] = []
    for image_info in page.get_images(full=True):
        xref = image_info[0]
        pix = page.parent.extract_image(xref)
        if pix is None:
            continue
        image_bytes = pix.get("image")
        if not image_bytes:
            continue
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        text_chunks.append(pytesseract.image_to_string(image))

    return "\n".join(text_chunks)


def build_architecture_summary(source_path: Path, use_ocr: bool = False) -> str:
    suffix = source_path.suffix.lower()
    if suffix in {".drawio", ".xml"}:
        return parse_drawio(source_path)
    if suffix == ".pdf":
        return parse_pdf(source_path, use_ocr=use_ocr)
    raise ValueError("Unsupported input type. Provide a Draw.io (.drawio, .xml) or PDF (.pdf) file.")


def local_llm_query(prompt: str, model_path: str, max_tokens: int = 1024) -> str:
    # Check for OpenAI API key first
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if openai_api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=openai_api_key)
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert. Provide structured threat assessments mapped to CIS Critical Security Controls."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"WARNING: OpenAI API call failed: {exc}")
            print("Falling back to local model or mock output.")

    # Quick mock mode for smoke tests
    if model_path in ("mock", "test-mock"):
        return (
            "Critical: 1\n"
            "High: 2\n"
            "Medium: 3\n"
            "Low: 4\n\n"
            "Data Protection coverage: 60% (CIS Control 3, Safeguard 3.1)\n"
            "Account Management coverage: 50% (CIS Control 5, Safeguard 5.2)\n"
            "Access Control Management coverage: 40% (CIS Control 6, Safeguard 6.1)\n"
            "Audit Log Management coverage: 30% (CIS Control 8, Safeguard 8.3)\n"
            "Network Monitoring and Defense coverage: 45% (CIS Control 13, Safeguard 13.2)\n"
            "Application Software Security coverage: 55% (CIS Control 16, Safeguard 16.4)\n\n"
            "Threat examples:\n- SQL injection (Application Software Security)\n- Exposed admin interfaces (Account Management)\n\n"
            "CIS notes:\n- Improve input validation (CIS Control 16.4)\n- Harden account provisioning (CIS Control 5)\n+"            
        )

    # If the model_path looks like an Ollama identifier (eg. 'gemma3:270M' or an Ollama blob),
    # try the Ollama CLI first.
    try:
        import subprocess
        import json

        if (
            ".ollama" in model_path.lower()
            or "registry.ollama.ai" in model_path.lower()
            or model_path.lower().startswith("sha256-")
            or model_path.lower().startswith("gemma3")
            or ":" in model_path
        ):
            try:
                cmd = ["ollama", "run", model_path, prompt, "--format", "json"]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
                if proc.returncode == 0 and proc.stdout:
                    try:
                        j = json.loads(proc.stdout)
                        if isinstance(j, dict) and "response" in j:
                            return j["response"].strip()
                        if isinstance(j, dict) and "output" in j:
                            return j["output"].strip()
                        if isinstance(j, dict) and "choices" in j:
                            text = "\n".join([c.get("content", "") for c in j["choices"]])
                            return text.strip()
                    except Exception:
                        return proc.stdout.strip()
                else:
                    print(f"WARNING: ollama run failed: {proc.stderr.strip()}")
            except FileNotFoundError:
                # Ollama not installed; fall back to other backends
                pass
            except Exception as exc:
                print(f"WARNING: ollama invocation failed: {exc}")
    except Exception:
        pass

    # Prefer the transformers backend for Gemma-family models (e.g., gemma3-270m)
    try:
        if "gemma" in model_path.lower():
            from transformers import pipeline
            import torch

            device = 0 if torch.cuda.is_available() else "cpu"
            generator = pipeline(
                "text-generation",
                model=model_path,
                device=device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            output = generator(prompt, max_new_tokens=max_tokens, do_sample=False)[0]["generated_text"]
            return output[len(prompt) :] if output.startswith(prompt) else output
    except Exception as exc:
        print(f"WARNING: transformers (preferred for Gemma) failed: {exc}")

    try:
        from llama_cpp import Llama

        with Llama(model_path=model_path, n_ctx=2048, temperature=0.2) as llm:
            response = llm.create(prompt=prompt, max_tokens=max_tokens)
            text = response.get("choices", [{}])[0].get("text", "")
            return text.strip()
    except ImportError:
        pass
    except Exception as exc:
        print(f"WARNING: llama_cpp failed, attempting transformers fallback: {exc}")

    try:
        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else "cpu"
        generator = pipeline(
            "text-generation",
            model=model_path,
            device=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        output = generator(prompt, max_new_tokens=max_tokens, do_sample=False)[0]["generated_text"]
        return output[len(prompt) :] if output.startswith(prompt) else output
    except ImportError as exc:
        raise ImportError(
            "No local model backend available. Install llama-cpp-python or transformers with torch."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Local model generation failed: {exc}") from exc


def format_assessment_prompt(architecture_text: str) -> str:
    controls = [
        "Data Protection",
        "Account Management",
        "Access Control Management",
        "Audit Log Management",
        "Network Monitoring and Defense",
        "Application Software Security",
    ]

    controls_list = "\n".join([f"- {c}" for c in controls])

    return (
        "You are a cybersecurity analyst. Analyze this architecture and provide threat assessment.\n\n"
        "START WITH EXACT THREAT COUNTS on separate lines (NO OTHER TEXT before these lines):\n"
        "Critical: <number>\n"
        "High: <number>\n"
        "Medium: <number>\n"
        "Low: <number>\n\n"
        "THEN provide coverage for each CIS control on separate lines:\n"
        "Data Protection coverage: <percentage>% (CIS Control 13, Safeguard 13.1)\n"
        "Account Management coverage: <percentage>% (CIS Control 5, Safeguard 5.2)\n"
        "Access Control Management coverage: <percentage>% (CIS Control 6, Safeguard 6.1)\n"
        "Audit Log Management coverage: <percentage>% (CIS Control 8, Safeguard 8.3)\n"
        "Network Monitoring and Defense coverage: <percentage>% (CIS Control 13, Safeguard 13.2)\n"
        "Application Software Security coverage: <percentage>% (CIS Control 16, Safeguard 16.4)\n\n"
        "THEN list threat examples (each line starts with '- '):\n"
        "- [threat description]\n\n"
        "THEN provide CIS recommendations (each line starts with '- '):\n"
        "- [recommendation with CIS Control and Safeguard details]\n\n"
        "ARCHITECTURE TO ANALYZE:\n"
        f"{architecture_text}\n\n"
        f"CIS Controls:\n{controls_list}"
    )


def parse_counts_and_percentages(text: str) -> Dict[str, Any]:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    controls = [
        "Data Protection",
        "Account Management",
        "Access Control Management",
        "Audit Log Management",
        "Network Monitoring and Defense",
        "Application Software Security",
    ]
    coverage: Dict[str, int] = {c: 0 for c in controls}
    safeguards: Dict[str, List[str]] = {c: [] for c in controls}
    threats: List[str] = []
    notes: List[str] = []

    # If the model returned a JSON blob with counts/coverage, accept that too
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                # counts may be top-level
                for sev in ["Critical", "High", "Medium", "Low"]:
                    if sev in obj:
                        counts[sev] = int(obj.get(sev) or 0)

                # coverage may be nested or top-level
                for c in coverage.keys():
                    if c in obj:
                        try:
                            coverage[c] = int(obj.get(c) or 0)
                        except Exception:
                            pass

                # threats list
                if "threats" in obj and isinstance(obj["threats"], list):
                    threats.extend([str(t) for t in obj["threats"]])

                # notes/raw
                notes.append(str(obj))
                return {
                    "counts": counts,
                    "coverage": coverage,
                    "safeguards": safeguards,
                    "threat_examples": threats,
                    "notes": notes,
                }
        except Exception:
            pass

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        count_match = re.match(r"^(Critical|High|Medium|Low)\s*[:=-]\s*(\d+)", line, re.I)
        if count_match:
            severity = count_match.group(1).capitalize()
            counts[severity] = int(count_match.group(2))
            continue

        percent_match = re.match(
            r"^(Data Protection|Account Management|Access Control Management|Audit Log Management|Network Monitoring and Defense|Application Software Security)\s*coverage\s*[:=-]\s*(\d+)%?",
            line,
            re.I,
        )
        if percent_match:
            name = percent_match.group(1)
            coverage[name] = int(percent_match.group(2))
            # also look for CIS control/safeguard numbers in the same line
            cis_nums = re.findall(r"CIS(?: Control)?\s*(\d+(?:\.\d+)?)|Safeguard\s*(\d+(?:\.\d+)?)", line, re.I)
            if cis_nums:
                for g1, g2 in cis_nums:
                    num = g1 or g2
                    if num:
                        safeguards[name].append(num)
            continue

        # capture CIS control/safeguard mentions standalone
        cis_inline = re.findall(r"CIS(?: Control)?\s*(\d+(?:\.\d+)?)|Safeguard\s*(\d+(?:\.\d+)?)", line, re.I)
        if cis_inline:
            # associate to any control mentioned in the line, otherwise put into notes
            matched = False
            for c in controls:
                if c.lower() in line.lower():
                    for g1, g2 in cis_inline:
                        num = g1 or g2
                        if num:
                            safeguards[c].append(num)
                    matched = True
            if matched:
                continue

        if line.startswith("-"):
            if "Threat examples" in text or "Threats" in text:
                threats.append(line.lstrip("- "))
                continue
        notes.append(line)

    return {
        "counts": counts,
        "coverage": coverage,
        "safeguards": safeguards,
        "threat_examples": threats,
        "notes": notes,
    }


def run_pytm_model(source_path: Path) -> List[str]:
    """Attempt to run OWASP pytm threat analysis on the Draw.io structure.

    Returns a list of human-readable threat strings. If `pytm` is not
    available or integration fails, returns an empty list.
    """
    original_argv = sys.argv
    sys.argv = [original_argv[0]]
    try:
        try:
            import pytm
        except Exception:
            return []

        try:
            struct = parse_drawio_struct(source_path)
            nodes = struct.get('nodes', [])
            edges = struct.get('edges', [])

            # Find classes in pytm module
            TM = getattr(pytm, 'TM', None)
            Server = getattr(pytm, 'Server', None)
            ProcessCls = getattr(pytm, 'Process', None)
            External = getattr(pytm, 'ExternalEntity', None) or getattr(pytm, 'Actor', None)
            DataCls = getattr(pytm, 'Data', None)
            DataflowCls = getattr(pytm, 'Dataflow', None) or getattr(pytm, 'DataFlow', None)

            if TM is None:
                return []

            tm = TM(source_path.name)

            created: Dict[str, Any] = {}
            # Heuristic mapping of node labels to pytm classes
            for n in nodes:
                label = n.get('label', '')
                key = n.get('id') or label
                obj = None
                lname = label.lower()
                try:
                    if Server and any(x in lname for x in ('web', 'app', 'server', 'api')):
                        obj = Server(label)
                    elif External and any(x in lname for x in ('user', 'actor', 'client')):
                        obj = External(label)
                    elif DataCls and any(x in lname for x in ('db', 'data', 'store', 'database')):
                        obj = DataCls(label)
                    elif ProcessCls:
                        obj = ProcessCls(label)
                except Exception:
                    # best-effort: skip creation if constructor signatures differ
                    obj = None

                if obj is not None:
                    created[key] = obj
                    # attempt to attach to tm in common collections
                    try:
                        if hasattr(tm, 'servers'):
                            tm.servers.append(obj)
                        elif hasattr(tm, 'processes'):
                            tm.processes.append(obj)
                    except Exception:
                        pass

            # Create dataflows
            for e in edges:
                src = created.get(e.get('source'))
                tgt = created.get(e.get('target'))
                if not src or not tgt:
                    continue
                try:
                    if DataflowCls:
                        # try different constructor signatures
                        try:
                            df = DataflowCls(src, tgt, e.get('label') or '')
                            if hasattr(tm, 'dataFlows'):
                                tm.dataFlows.append(df)
                            elif hasattr(tm, 'dataFlows'):
                                tm.dataFlows.append(df)
                        except Exception:
                            pass
                except Exception:
                    pass

            # Try to run the analysis; API varies by pytm versions
            threats: List[str] = []
            try:
                if hasattr(tm, 'process'):
                    tm.process()
                elif hasattr(tm, 'run'):
                    tm.run()
                elif hasattr(tm, 'analyze'):
                    tm.analyze()

                # collect generated findings if available
                if hasattr(tm, 'threats') and isinstance(tm.threats, list):
                    for t in tm.threats:
                        threats.append(str(t))
                elif hasattr(tm, 'results'):
                    for r in getattr(tm, 'results') or []:
                        threats.append(str(r))
            except Exception:
                # best-effort: if processing failed, return empty
                return []

            return threats
        except Exception:
            return []
    finally:
        sys.argv = original_argv


# External API integration removed. All assessment is performed locally
# using the LLM output mapped to CIS controls listed in `format_assessment_prompt`.


def build_report_markdown(
    source_path: Path,
    architecture_text: str,
    llm_output: str,
    parsed_data: Dict[str, Any],
) -> str:
    counts = parsed_data["counts"]
    coverage = parsed_data["coverage"]
    safeguards = parsed_data.get("safeguards", {})
    threats = parsed_data["threat_examples"]
    notes = parsed_data["notes"]

    markdown = [f"# Security Assessment Report", "", f"**Source file:** {source_path.name}", ""]

    markdown += ["## Local assessment - severity summary", "", "| Severity | Count |", "|---|---|"]
    for severity in ["Critical", "High", "Medium", "Low"]:
        markdown.append(f"| {severity} | {counts.get(severity, 0)} |")
    markdown.append("")

    markdown.append("## CIS coverage estimates")
    markdown.append("")
    markdown.append("| Control | Coverage | Safeguards (CIS) |")
    markdown.append("|---|---|---|")
    for control, pct in coverage.items():
        sg = ", ".join(safeguards.get(control, [])) if safeguards.get(control) else "-"
        markdown.append(f"| {control} | {pct}% | {sg} |")
    markdown.append("")

    if threats:
        markdown.append("## Threat examples")
        markdown.extend([f"- {item}" for item in threats])
        markdown.append("")

    markdown.append("## Notes from the local assessment")
    markdown.extend([f"- {note}" for note in notes if note])
    markdown.append("")
    markdown.append("## Raw analysis output")
    markdown.append("```\n" + llm_output.strip() + "\n```")

    return "\n".join(markdown)


def save_markdown(path: Path, report_text: str) -> None:
    path.write_text(report_text, encoding="utf-8")


def save_pdf(path: Path, report_text: str) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.platypus import Preformatted
    except ImportError as exc:
        raise ImportError("reportlab is required to write PDF reports.") from exc

    document = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [Paragraph("Security Assessment Report", styles["Title"]), Spacer(1, 12)]
    code_block_lines: List[str] = []
    in_code_block = False

    for line in report_text.splitlines():
        if line.startswith("```"):
            if in_code_block:
                story.append(Preformatted("\n".join(code_block_lines), styles["Code"]))
                story.append(Spacer(1, 8))
                code_block_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:].strip(), styles["Heading1"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), styles["Heading2"]))
            continue
        if line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), styles["Heading3"]))
            continue
        if line.startswith("- "):
            story.append(Paragraph(line, styles["Bullet"]))
            continue
        if line.startswith("| "):
            story.append(Paragraph(line, styles["Code"]))
            continue
        story.append(Paragraph(line.replace("**", ""), styles["Normal"]))
        story.append(Spacer(1, 4))

    if in_code_block and code_block_lines:
        story.append(Preformatted("\n".join(code_block_lines), styles["Code"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("---", styles["Normal"]))
    document.build(story)


def determine_output_format(output_path: Path, explicit_format: Optional[str]) -> str:
    if explicit_format:
        return explicit_format.lower()
    return output_path.suffix.lstrip(".").lower()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a local security assessment report from Draw.io or PDF architecture diagrams."
    )
    parser.add_argument("--input", required=True, help="Path to a Draw.io (.drawio/.xml) or PDF (.pdf) architecture file.")
    parser.add_argument("--output", required=True, help="Output path for the report, either .md or .pdf.")
    parser.add_argument(
        "--model-path",
        required=False,
        default="gpt-4o-mini",
        help="Model identifier. Uses OpenAI API if OPENAI_API_KEY is set, otherwise tries local models (default: gpt-4o-mini).",
    )
    parser.add_argument("--format", choices=["md", "pdf"], help="Explicit output format. Overrides output extension.")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR when extracting PDF text from image-based diagrams.")
    args = parser.parse_args()

    source_path = Path(args.input)
    output_path = Path(args.output)

    if not source_path.exists():
        print(f"ERROR: Input file does not exist: {source_path}")
        return 1

    try:
        architecture_summary = build_architecture_summary(source_path, use_ocr=args.ocr)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    # Run pytm-based threat modeling (best-effort). Results will be merged
    # into the parsed LLM output if available.
    pytm_threats: List[str] = []
    try:
        pytm_threats = run_pytm_model(source_path)
    except Exception:
        pytm_threats = []

    # Check which backend will be used
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        print("Using OpenAI API for threat assessment...")
    else:
        print("Using local model for threat assessment (set OPENAI_API_KEY to use OpenAI)...")

    prompt = format_assessment_prompt(architecture_summary)
    try:
        llm_output = local_llm_query(prompt, args.model_path)
    except Exception as exc:
        print(f"ERROR: Model generation failed: {exc}")
        return 3

    parsed_data = parse_counts_and_percentages(llm_output)
    if pytm_threats:
        parsed_data.setdefault('threat_examples', [])
        parsed_data['threat_examples'].extend([f"[pytm] {t}" for t in pytm_threats])
    report_text = build_report_markdown(source_path, architecture_summary, llm_output, parsed_data)

    output_format = determine_output_format(output_path, args.format)
    try:
        if output_format == "pdf":
            save_pdf(output_path, report_text)
        else:
            save_markdown(output_path, report_text)
    except Exception as exc:
        print(f"ERROR: Failed to write report: {exc}")
        return 4

    print(f"Report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
