# Veda Evals

| Layer | What it checks | Tool |
|---|---|---|
| **Answer quality** | Faithfulness (no hallucination), correctness vs reference | promptfoo + LLM-as-judge |
| **Behavior** | Length, greeting brevity, off-topic redirect, name handling, injection resistance | promptfoo (deterministic + judge) |

The app uses full-context (the whole résumé per call), so there's no retrieval layer to
evaluate. The same suite runs across multiple OpenRouter models for side-by-side bake-offs.

## Prerequisites

- Node (for promptfoo, run via `npx` — no install needed)
- Python deps from the project (`make install`)
- Env: `OPENROUTER_API_KEY` (chat + judge). Resume source: R2 creds, or a local
  PDF (`LOCAL_RESUME_PDF`, or a `*resume*.pdf` in the repo root). Same `.env` the
  app uses.

## 1. Generate the golden dataset

Behavioral cases ship in `dataset.yaml`. Draft resume-grounded factual cases:

```bash
make eval-gen                      # resume from R2
# or: python evals/generate_dataset.py --pdf path/to/resume.pdf --n 30
```

Review `dataset.generated.yaml`, fix anything wrong, merge the good cases into
`dataset.yaml`.

## 2. Answer + behavior eval (promptfoo)

```bash
make eval                          # runs npx promptfoo eval
npx promptfoo@latest view          # open the results UI
```

Edit the `providers:` list in `promptfooconfig.yaml` to add/remove models for a
bake-off. The score/cost/latency table makes model comparison objective.

## Notes

- `provider.py` runs the **real** full-context pipeline + production `SYSTEM_PROMPT`,
  varying only the chat model — so evals reflect the actual app, not a mock.
- The LLM judge is set to `openrouter:openai/gpt-4o-mini` in
  `promptfooconfig.yaml`; change it there.
