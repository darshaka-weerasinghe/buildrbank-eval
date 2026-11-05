"""Send evals/dataset.yaml to Langfuse as a dataset.

The YAML in this repository is the source of truth. This script mirrors it
into Langfuse so experiment runs can be compared against each other in the
UI. Re-running it is safe: items carry a stable `id` taken from the YAML, so
an edited reference updates that item instead of creating a duplicate.

    python evals/push_dataset.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import settings          # noqa: E402  - configures env before langfuse
settings.configure()

from langfuse import Langfuse     # noqa: E402

DATASET = "buildrbank-support"
HERE = Path(__file__).resolve().parent


def main() -> int:
    items = yaml.safe_load((HERE / "dataset.yaml").read_text(encoding="utf-8"))
    lf = Langfuse()

    lf.create_dataset(
        name=DATASET,
        description="Support questions with reference answers. Mixed on purpose: "
                    "facts from the handbook, refusals the agent must make, and "
                    "one thing the handbook does not cover.",
    )

    for it in items:
        lf.create_dataset_item(
            dataset_name=DATASET,
            id=it["id"],                      # stable: edit, do not duplicate
            input=it["question"],
            expected_output=it["reference"],
            metadata={"kind": it["kind"],
                      **({"behavior": it["behavior"]} if it.get("behavior") else {})},
        )
        print(f"  {it['id']:<26} {it['kind']}")

    lf.flush()
    print(f"\n{len(items)} items in dataset '{DATASET}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
