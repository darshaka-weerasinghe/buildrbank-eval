# Evaluation

Observability tells you what happened. It cannot tell you whether the answer
was any good. That needs a reference - someone writing down what "correct"
means - and that is what lives here.

## Running it

```bash
python evals/push_dataset.py              # mirror the YAML into Langfuse
python evals/run_eval.py --name baseline  # run the agent over it, graded
```

`--name` labels the run so you can tell two runs apart in the Langfuse UI.
Runs execute one item at a time, which is slower but stays inside model rate
limits and keeps the evidence capture correct.

## The dataset

`dataset.yaml` is the source of truth, in the repository, reviewed like any
other change. Langfuse is a mirror - items carry stable ids, so editing a
reference updates the item instead of creating a duplicate.

Ten questions, mixed on purpose:

| kind | what it tests |
| --- | --- |
| `fact` | the answer is in the handbook, with exact figures |
| `action` | the customer needs something **done**, not explained |
| `refusal` | the agent must decline - investment advice, another customer's data |
| `unknown` | the handbook does not cover it, so it must say so rather than invent |

A test set of only easy questions tells you nothing.

## What the first two runs found

**Run 1, `baseline`: mean 8.70 / 10, nine of ten passed.**

The failure was `lost-card`, at 4/10. The agent froze the card and said
nothing else - no emergency number, no mention of the app. Reading `bb-voice`
explained why:

```
- SHORT: usually one sentence, never more than two.
- Do NOT volunteer costs, fees, or later steps of the procedure
  unless the customer explicitly asked about them
```

The agent was obeying its prompt exactly. Brevity was outranking telling a
customer whose card had just been stolen that a 24-hour line exists. That is
not a bug in the code - it is two requirements colliding, and nobody noticed
for a month because nobody had written down what a complete answer looks like.

**Run 2, `with-safety-carveout`: mean 9.00 / 10, ten of ten passed.**

One new version of `bb-voice` in Langfuse, carrying an exception for lost or
stolen cards, fraud and unauthorised transactions. `lost-card` went 4 -> 7 and
passed. No deploy, no commit, no restart - the running app picked up the new
prompt on its next fetch. Roll back by moving the `production` label.

## Two things to be honest about

**Scores wobble.** Between those runs `unknown-crypto` went 9 -> 7, and
`bb-voice` has nothing to do with that path. Models are not deterministic.
Read the aggregate, not one row, and do not claim a win from a single run.

**Your evaluator can be wrong.** Before this week the judge was called with
only the question and the answer - never the retrieved evidence - so it could
not tell a figure quoted from the handbook from one the model invented. A
month of correct answers scored a mean of 3.5/10. Passing `evidence` to it
moved the same answer, graded by the same model, from 3 to 9.

The thing that grades your system is part of your system.
