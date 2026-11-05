"""Grade one real answer twice: once blindfolded, once not.

This is the whole of the first half in about twenty seconds. The agent runs
a real turn, and then the SAME judge model grades the SAME answer two ways -
without the retrieved evidence, as live traffic was graded until this week,
and with it.

    python evals/judge_demo.py
    python evals/judge_demo.py --question "What interest does a savings account pay?"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import settings          # noqa: E402  - configures env first
settings.configure()

import buildrbank.orchestration.graph as G          # noqa: E402
from buildrbank.app import build_app                # noqa: E402
from buildrbank.orchestration import judge          # noqa: E402

DEFAULT_Q = "What are your wire transfer fees?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default=DEFAULT_Q)
    q = ap.parse_args().question

    # Take the evidence on its way past, and skip the agent's own judge so we
    # are not paying for a verdict we are about to replace.
    seen: dict[str, str] = {}
    G.verdict = lambda _q, _a, **kw: (seen.__setitem__("evidence", kw.get("evidence") or ""),
                                      {"score": 0, "pass": False, "reason": "skipped"})[1]
    G.score_trace = lambda _v: None

    agent = build_app()
    res = agent.turn(user_id="demo", thread_id="judge-demo", text=q,
                     email="isuru@example.com")
    evidence = seen.get("evidence", "")

    print(f"\nQUESTION  {q}")
    print(f"ROUTE     {res.route}")
    print(f"ANSWER    {res.reply.strip()[:300]}")
    print(f"RETRIEVED {len(evidence)} characters of the bank's own data\n")

    blind = judge.verdict(question=q, answer=res.reply)
    seeing = judge.verdict(question=q, answer=res.reply, evidence=evidence)

    for label, v in (("WITHOUT the evidence", blind), ("WITH the evidence", seeing)):
        print(f"  {label}")
        print(f"    score {v.get('score')}   pass {v.get('pass')}")
        print(f"    {v.get('reason')}\n")

    agent.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
