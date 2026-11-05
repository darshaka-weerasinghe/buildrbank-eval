"""Run the agent over the dataset and grade every answer against its reference.

    python evals/run_eval.py                 # run everything
    python evals/run_eval.py --name "no-evidence"   # label this run

Live traffic is graded without a reference, because there isn't one - the
judge only sees the question, the answer and what was retrieved. Here there
IS a reference, so the judge compares against a known-good answer. That is
the difference between watching production and testing it.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import settings          # noqa: E402  - must run before anything else
settings.configure()

from langfuse import Langfuse                              # noqa: E402
from langfuse.experiment import Evaluation                 # noqa: E402
import buildrbank.orchestration.graph as G                 # noqa: E402
from buildrbank.app import build_app                       # noqa: E402
from buildrbank.orchestration import judge                 # noqa: E402

DATASET = "buildrbank-support"

# What the agent retrieved for the item being processed right now. A plain
# module global is safe only because max_concurrency is 1 below - see there.
_current_id: str = ""
_evidence: dict[str, str] = {}


def _intercept_live_judge():
    """Capture the retrieved evidence, and skip the agent's own judge.

    During a run the agent would otherwise grade itself a second time, with
    no reference and no benefit - one wasted model call per item. We take the
    evidence on the way past and return a placeholder.
    """
    def capture(_question, _answer, **kw):
        _evidence[_current_id] = kw.get("evidence") or ""
        return {"score": 0, "pass": False, "reason": "skipped during eval run"}

    G.verdict = capture
    G.score_trace = lambda _v: None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="baseline",
                    help="label for this run, so you can tell runs apart")
    ap.add_argument("--no-evidence", action="store_true",
                    help="withhold the retrieved evidence from the judge. Note "
                         "what this does NOT do: scores stay high, because the "
                         "reference already says what correct looks like. That "
                         "is the point of a test set - production never has one.")
    args = ap.parse_args()

    _intercept_live_judge()
    agent = build_app()
    lf = Langfuse()
    dataset = lf.get_dataset(DATASET)
    stamp = uuid.uuid4().hex[:6]

    def task(*, item, **_):
        """One dataset item through the real agent."""
        global _current_id
        _current_id = (item.id if hasattr(item, "id") else item["metadata"]["id"])
        # A fresh thread per item: the agent remembers conversations, and we do
        # not want question 3 answered in the light of question 2.
        res = agent.turn(user_id="eval",
                         thread_id=f"eval-{stamp}-{_current_id}",
                         text=item.input,
                         email="isuru@example.com")
        return res.reply

    def graded(*, input, output, expected_output, metadata=None, **_):
        """The judge, this time with a reference AND the retrieved evidence."""
        meta = metadata or {}
        item_id = meta.get("id") or _current_id
        v = judge.verdict(question=input,
                          answer=output or "",
                          reference=expected_output,
                          behavior=meta.get("behavior"),
                          evidence="" if args.no_evidence
                                   else _evidence.get(item_id, ""))
        return [
            Evaluation(name="judge_score", value=float(v.get("score", 0)),
                       comment=str(v.get("reason", "")), data_type="NUMERIC"),
            Evaluation(name="passed", value=bool(v.get("pass", False)),
                       data_type="BOOLEAN"),
        ]

    result = lf.run_experiment(
        name=f"buildrbank {args.name}",
        run_name=f"{args.name}-{stamp}",
        description="Agent answers graded against reference answers.",
        data=dataset.items,
        task=task,
        evaluators=[graded],
        # One at a time. The agent keeps conversation state and the evidence
        # capture above is a single global; and it keeps us inside the model
        # provider's rate limits.
        max_concurrency=1,
    )

    if args.no_evidence:
        print("\n  (graded without the retrieved evidence - the reference is "
              "carrying it)")
    print(f"\n  {'item':<26}{'score':>6}  {'pass':<6}")
    print("  " + "-" * 44)
    scores, passes = [], []
    for r in result.item_results:
        evs = {e.name: e.value for e in (r.evaluations or [])}
        s, p = evs.get("judge_score"), evs.get("passed")
        if s is not None:
            scores.append(s)
            passes.append(bool(p))
        iid = getattr(r.item, "id", "?")
        print(f"  {str(iid):<26}{s if s is not None else '-':>6}  {str(p):<6}")

    if scores:
        print("  " + "-" * 44)
        print(f"  mean {sum(scores)/len(scores):.2f} / 10"
              f"   passed {sum(passes)}/{len(passes)}")
    if getattr(result, "dataset_run_url", None):
        print(f"\n  {result.dataset_run_url}")

    agent.close()
    lf.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
