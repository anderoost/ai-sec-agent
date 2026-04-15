#!/usr/bin/env python3
"""Local security assessment agent for Draw.io and PDF architecture diagrams."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def format_irius_prompt(architecture_text: str) -> str:
    return (
        "You are a cybersecurity analyst reviewing an architecture diagram. "
        "Provide a concise Irius Risk assessment and CIS coverage estimate for Application Software Security "
        "and Data Protection controls.\n\n"
        "Architecture description:\n"
        f"{architecture_text}\n\n"
        "Respond with exact lines for counts and percentages:\n"
        "Critical: <number>\n"
        "High: <number>\n"
        "Medium: <number>\n"
        "Low: <number>\n"
        "Application Software Security coverage: <percentage>%\n"
        "Data Protection coverage: <percentage>%\n"
        "Threat examples:\n"
        "- ...\n"
        "CIS notes:\n"
        "- ...\n"
    )


def parse_counts_and_percentages(text: str) -> Dict[str, Any]:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    coverage = {
        "Application Software Security": 0,
        "Data Protection": 0,
    }
    threats: List[str] = []
    notes: List[str] = []

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
            r"^(Application Software Security|Data Protection) coverage\s*[:=-]\s*(\d+)%?",
            line,
            re.I,
        )
        if percent_match:
            name = percent_match.group(1)
            coverage[name] = int(percent_match.group(2))
            continue

        if line.startswith("-"):
            if "Threat examples" in text or "Threats" in text:
                threats.append(line.lstrip("- "))
                continue
        notes.append(line)

    return {
        "counts": counts,
        "coverage": coverage,
        "threat_examples": threats,
        "notes": notes,
    }


def query_irius_risk(
    architecture_text: str,
    api_url: Optional[str],
    api_key: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not api_url or not api_key:
        return None

    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"architecture_description": architecture_text}
    endpoints = [api_url]

    if api_url.endswith("/"):
        endpoints.append(api_url + "api/1/threats")
        endpoints.append(api_url + "v1/threats")
    else:
        endpoints.append(api_url + "/api/1/threats")
        endpoints.append(api_url + "/v1/threats")

    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
            if response.status_code != 200:
                continue
            data = response.json()
            return parse_irius_response(data)
        except Exception:
            continue

    return None


def parse_irius_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    threat_items: List[Dict[str, Any]] = []

    for item in payload.get("threats", []) or []:
        severity = (item.get("severity") or item.get("risk") or item.get("priority") or "").capitalize()
        if severity in counts:
            counts[severity] += 1
        else:
            if severity:
                counts[severity] = counts.get(severity, 0) + 1
        threat_items.append(item)

    return {
        "counts": counts,
        "threats": threat_items,
        "raw": payload,
    }


def build_report_markdown(
    source_path: Path,
    architecture_text: str,
    llm_output: str,
    iriussummary: Optional[Dict[str, Any]],
    parsed_data: Dict[str, Any],
) -> str:
    counts = parsed_data["counts"]
    coverage = parsed_data["coverage"]
    threats = parsed_data["threat_examples"]
    notes = parsed_data["notes"]

    markdown = [f"# Security Assessment Report", "", f"**Source file:** {source_path.name}", ""]

    if iriussummary:
        api_counts = iriussummary.get("counts", {})
        markdown += ["## Irius Risk API summary", "", "| Severity | Count |", "|---|---|"]
        for severity in ["Critical", "High", "Medium", "Low"]:
            markdown.append(f"| {severity} | {api_counts.get(severity, 0)} |")
        markdown.append("")
        markdown.append("### Irius API raw findings")
        markdown.append("```json")
        markdown.append(json.dumps(iriussummary.get("raw", {}), indent=2))
        markdown.append("```")
        markdown.append("")

    markdown += ["## Local Irius Risk estimate", "", "| Severity | Count |", "|---|---|"]
    for severity in ["Critical", "High", "Medium", "Low"]:
        markdown.append(f"| {severity} | {counts.get(severity, 0)} |")
    markdown.append("")

    markdown.append("## CIS coverage estimates")
    markdown.append("")
    markdown.append("| Control | Coverage |")
    markdown.append("|---|---|")
    markdown.append(f"| Application Software Security | {coverage['Application Software Security']}% |")
    markdown.append(f"| Data Protection | {coverage['Data Protection']}% |")
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
        required=True,
        help="Path to a local open-source model file (for example llama-2-7b-chat.gguf or a local transformers model path).",
    )
    parser.add_argument("--irius-api-url", help="Optional Irius Risk API hostname or endpoint.")
    parser.add_argument("--irius-api-key", help="Optional Bearer API key for Irius Risk.")
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

    prompt = format_irius_prompt(architecture_summary)
    try:
        llm_output = local_llm_query(prompt, args.model_path)
    except Exception as exc:
        print(f"ERROR: Local model generation failed: {exc}")
        return 3

    parsed_data = parse_counts_and_percentages(llm_output)
    iriussummary = query_irius_risk(architecture_summary, args.irius_api_url, args.irius_api_key)
    report_text = build_report_markdown(source_path, architecture_summary, llm_output, iriussummary, parsed_data)

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
