"""Draft resume-grounded eval cases for Veda.

Pulls the resume text (from R2, or a local --pdf), asks an OpenRouter model to
generate factual Q&A grounded ONLY in the resume, and writes them to
dataset.generated.yaml in the eval format for human review before merging into
dataset.yaml.

Usage:
  python evals/generate_dataset.py                 # resume from R2
  python evals/generate_dataset.py --pdf resume.pdf
  python evals/generate_dataset.py --n 30 --model deepseek/deepseek-v4-pro

Needs: OPENROUTER_API_KEY  (+ R2 creds if not using --pdf)
"""
import os
import sys
import json
import argparse

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_router import _get_client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dataset.generated.yaml")

GEN_SYSTEM = (
    "You write evaluation datasets for a resume Q&A assistant. "
    "You produce ONLY factual questions answerable from the provided resume text, "
    "plus grounding metadata. Never invent facts not present in the resume."
)

GEN_INSTRUCTIONS = """\
From the resume below, generate {n} diverse evaluation cases a website visitor might ask.
Cover: work history, specific roles/titles, skills/technologies, education, projects, and
achievements. Mix simple lookups and a few multi-fact questions.

Return ONLY a JSON array. Each element:
{{
  "question": "a natural visitor question",
  "reference": "a concise correct answer grounded in the resume (<40 words)",
  "expected_context": ["2-4 short verbatim phrases from the resume that retrieval should surface"],
  "category": "experience|skills|education|projects|achievements"
}}

Resume text:
---
{resume}
---
"""


def get_resume_text(pdf_path: str | None) -> str:
    if pdf_path:
        from load_resume import extract_text_from_pdf
        return extract_text_from_pdf(pdf_path)
    from load_resume import get_resume_from_r2
    return get_resume_from_r2()


def to_case(item: dict) -> dict:
    """Convert a generated item into the eval dataset shape."""
    return {
        "description": f"{item.get('category', 'fact')}: {item['question']}",
        "vars": {"question": item["question"]},
        "expected_context": item.get("expected_context", []),
        "assert": [
            {
                "type": "llm-rubric",
                "value": (
                    "The answer is consistent with this reference and invents no facts "
                    f"beyond Amit's resume. Reference: {item.get('reference', '').strip()}"
                ),
            }
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="local resume PDF (otherwise pulled from R2)")
    ap.add_argument("--n", type=int, default=25, help="number of cases to generate")
    ap.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-pro"),
                    help="OpenRouter model used to generate the cases")
    args = ap.parse_args()

    resume = get_resume_text(args.pdf)
    if not resume.strip():
        print("Empty resume text — aborting.")
        return 1

    completion = _get_client().chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": GEN_SYSTEM},
            {"role": "user", "content": GEN_INSTRUCTIONS.format(n=args.n, resume=resume)},
        ],
        response_format={"type": "json_object"},
        timeout=120,
    )
    raw = completion.choices[0].message.content.strip()

    # Model may return a bare array or an object wrapping one.
    parsed = json.loads(raw)
    items = parsed if isinstance(parsed, list) else next(
        (v for v in parsed.values() if isinstance(v, list)), []
    )
    if not items:
        print("Could not parse generated cases. Raw output:\n", raw[:2000])
        return 1

    cases = [to_case(it) for it in items if it.get("question")]
    header = (
        "# AUTO-GENERATED draft — REVIEW before merging into dataset.yaml.\n"
        f"# Source model: {args.model}; cases: {len(cases)}\n"
    )
    with open(OUT, "w") as f:
        f.write(header)
        yaml.safe_dump(cases, f, sort_keys=False, allow_unicode=True, width=100)

    print(f"Wrote {len(cases)} draft cases to {OUT}")
    print("Review them, fix any inaccuracies, then merge the good ones into dataset.yaml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
