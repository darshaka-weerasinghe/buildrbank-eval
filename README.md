# BuildrBank · is it actually any good?

Week 05 got the agent running. Week 06 made every push deploy it. Week 08 made
the server itself a file you can rebuild in four minutes.

None of that tells you whether the answers are **right**.

Your `/health` endpoint can return `ok`, your pipeline can go green, your
dashboard can be all zeros — and the agent can still quote a fee that does not
exist. Infrastructure monitoring is blind to that by design. It watches the
machine. Nobody has been watching the answers.

Except something has, the whole time.

## What was already here

This application has been fully instrumented since Week 05. Open
`vendor/buildrbank/observability.py` and you will find:

- every step of a turn traced — router, retrieval, embeddings, tools,
  generation, guardrails
- `thread_id` doubling as the Langfuse `session_id`, so a conversation reads
  as one session
- account numbers masked **client-side**, before anything leaves the machine
- model and token usage recorded per generation, so every turn has a cost
- an LLM judge grading answers 0-10 and writing the verdict back onto the exact
  trace it graded

Nobody looked. That is this week's first lesson, and it costs nothing to fix.

## What this week adds

**A judge that can see.** `orchestration/judge.py` graded every answer without
ever being shown what the agent retrieved. It could not tell a figure quoted
from the handbook apart from one the model invented — so its rubric's
"invents fees, rates, policies" band swallowed every correct, specific answer.

A month of traffic scored a mean of **3.5 / 10**, failing 11 times out of 13.
The agent was right. The evaluator was blind.

The fix is two lines. `BBState` already carried the retrieved text; the judge
node simply never passed it:

```python
v = verdict(state["message"], state.get("reply", ""),
            evidence=state.get("evidence", ""))
```

Same question, same answer, same judge model:

| | Score | Why |
| --- | --- | --- |
| Before | **3** · failed | *"specific fee figures without any evidence that these come from the bank's actual data"* |
| After | **9** · passed | *"accurately cited all wire transfer fees from the retrieved evidence"* |

**Your evaluator is a system too, and it can be wrong in ways that look exactly
like your application being wrong.**

**Datasets and experiments.** Coming next: a set of questions with reference
answers, a runner that grades the agent against them, and the comparison that
tells you whether a change made things better or only different.

## What carries over unchanged

`infra/` still builds and prepares the server (Terraform + Ansible, Week 08) and
`.github/workflows/pipeline.yml` still deploys on push (Week 06). The image is
`buildrbank-eval` so it does not overwrite last week's tags.

## Start here

The step-by-step sheet is being written. Until then, `python scripts/check.py`
verifies your environment and `.env.example` lists what it needs.

> **One thing that will bite you.** OpenRouter bills from an account balance,
> not from the per-key limit shown on the keys page. A new account's signup
> credit runs out quietly, and the failure is partial — small calls succeed,
> real ones return `402`. Check
> [openrouter.ai/settings/credits](https://openrouter.ai/settings/credits).
