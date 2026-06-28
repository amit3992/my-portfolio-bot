"""promptfoo custom provider for Veda.

Runs the *real* RAG pipeline (FAISS retrieval + the production SYSTEM_PROMPT)
and calls a configurable OpenRouter model, so promptfoo can compare models
side-by-side over the same retrieval.

promptfoo calls `call_api(prompt, options, context)`:
  - `prompt`   : the rendered prompt — here just the visitor's question
  - `options`  : provider config from promptfooconfig.yaml (we read options["config"]["model"])
  - returns    : {"output": str, "tokenUsage": {...}}
"""
import os
import sys

# Make the project root importable when promptfoo runs this file from evals/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_engine import get_resume_text  # noqa: E402
from llm_router import SYSTEM_PROMPT, format_chatbot_response, _get_client  # noqa: E402


def _build_rag_prompt(question: str) -> str:
    # Mirrors app.build_prompt() (full resume in context, minus the DB knowledge
    # snippets, which are environment-specific and would make evals non-deterministic).
    return f"Amit's resume:\n{get_resume_text()}\n\nVisitor's message: {question}"


def call_api(prompt, options, context):
    config = (options or {}).get("config", {}) or {}
    model = config.get("model") or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

    question = prompt if isinstance(prompt, str) else str(prompt)

    try:
        rag_prompt = _build_rag_prompt(question)
        completion = _get_client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": rag_prompt},
            ],
            timeout=60,
        )
        text = format_chatbot_response(completion.choices[0].message.content)
        usage = getattr(completion, "usage", None)
        result = {"output": text}
        if usage is not None:
            result["tokenUsage"] = {
                "prompt": usage.prompt_tokens,
                "completion": usage.completion_tokens,
                "total": usage.total_tokens,
            }
        return result
    except Exception as e:  # promptfoo expects errors surfaced in the result
        return {"error": str(e)}
