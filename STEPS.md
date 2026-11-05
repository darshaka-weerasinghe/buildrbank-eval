# Is it any good? — the whole thing, step by step

**The repository:** <https://github.com/darshaka-weerasinghe/buildrbank-eval>

Eighteen steps. By the end you will have found out that your agent has been
scoring 3.5 out of 10 for a month, worked out that the agent was not the
problem, written down what "correct" means for ten questions, and proved that
a change you made actually helped.

> **Copy commands from [this file on GitHub](https://github.com/darshaka-weerasinghe/buildrbank-eval/blob/main/STEPS.md),
> not from the PDF handout.** The handout's font joins `--` and `//` into one
> character when you copy it, which breaks `--name` and `https://` in ways the
> error message disguises.

**What this costs.** No servers this week - everything runs on your laptop.
What it does cost is model calls: roughly 3 for the judge demo and about 30
for each full evaluation run, and you will run three. Budget a few US dollars
of OpenRouter credit. Step 4 is about exactly that, and it is not optional.

---

## Part A · On your laptop

### 1 · Fork it, and turn Actions on

Open the repository and press **Fork**, top right:

<https://github.com/darshaka-weerasinghe/buildrbank-eval>

Then open the **Actions** tab of *your fork*. GitHub disables workflows on a
new fork and shows a yellow banner - click **I understand my workflows, go
ahead and enable them**. You will not use the pipeline much this week, but a
fork with Actions switched off silently does nothing when you push, and that
is a confusing thing to discover later.

✓ The Actions tab shows **Test, build, deploy** with no yellow banner.

### 2 · Clone your fork

```bash
git clone https://github.com/YOUR-NAME/buildrbank-eval.git
cd buildrbank-eval
```

Put it wherever you keep your work. It is self-contained.

✓ `ls` shows `app`, `evals` and `vendor`.

### 3 · Bring your `.env` across, and wake Supabase

Everything here is ready except your keys. That is the only thing you need
from a previous week, because it was never in git.

```bash
cp /PATH/TO/YOUR/.env .env
```

Then open [supabase.com/dashboard](https://supabase.com/dashboard) and look at
the project your `SUPABASE_URL` points at. Free projects **pause after a week
of no use** and must be resumed by hand - there is a **Restore** or **Resume**
button on the project page. Click it and wait for the dashboard to say active.

> **Why this matters.** A dead Supabase does not stop the app from starting.
> It stops it from answering, and the error you eventually see is
> `ConnectError: [Errno -2] Name or service not known`, which never mentions
> Supabase at all.

✓ The Supabase dashboard shows your project as **active**.

### 4 · Put money in OpenRouter

This is the step everyone skips, and it is the one that stops the session.

Go to [openrouter.ai/settings/credits](https://openrouter.ai/settings/credits)
and check the balance. **Not the keys page** - the "key limit" there is a
spending cap, not money. A $50 cap on an empty account buys nothing.

New accounts get a small signup credit which quietly runs out. When it does,
the failure is *partial*: short calls still succeed and real ones return
`402`, so the app half-works and the router replies while the answer dies.

✓ The credits page shows a non-zero balance. A few dollars is plenty.

### 5 · Install and prove it works

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/check.py
```

Windows: `.venv\Scripts\activate`, and use `python`, not `python3`.

✓ Six green ticks, ending with one full message through the agent.

> **`401 invalid x-api-key` when your key is fine?** Check what step 1 of the
> output prints for `llm_via`. If it says `api.anthropic.com` instead of
> `openrouter.ai`, something in your shell has already set
> `ANTHROPIC_BASE_URL` - Claude Code does this - and your OpenRouter key is
> being sent to the wrong company. `unset ANTHROPIC_BASE_URL` and try again.

---

## Part B · What has been recorded all along

### 6 · Open a trace

Sign in at [cloud.langfuse.com](https://cloud.langfuse.com) and open the
**Tracing** view. Every message you have ever sent this agent is in there,
going back to Week 05. Open the most recent `bb-turn` and expand it.

```
SPAN        bb-turn
 GENERATION  router            → "policy"
 TOOL        search_policy
  RETRIEVER   search_chunks
  EMBEDDING   embed
 GUARDRAIL   gate_context
 GENERATION  answer_policy
 EVALUATOR   verdict
 GUARDRAIL   gate_output
```

Read it top to bottom. It decided something, went looking for evidence, was
checked on the way in and the way out, and was graded. Click any step to see
exactly what went in and what came out.

✓ You can say, out loud, why the agent answered the way it did.

### 7 · Notice what a trace costs, and what it holds

Still in that trace, look at each `GENERATION`: the model and the token count
are recorded, so every turn has a price. The router uses a cheap model, the
answer an expensive one, and the judge is a third call you may not have been
counting.

Now look at what is stored. A trace holds **everything the model saw** - the
customer's words, their account, whatever you retrieved about them. Open
`vendor/buildrbank/observability.py`:

```python
_ACC_RE = re.compile(r"ACC-\d{4,}")
# runs on every traced input and output, before upload
```

Account numbers are masked on your machine before anything leaves it.

✓ You can find a masked `[REDACTED-ACCOUNT]` in a trace.

### 8 · Find the scores

In Langfuse, open **Scores**, or filter traces by `judge_score`. Every answer
this agent has given has been graded 0-10 by a second model.

```
mean 3.54 / 10        passed 2        failed 11
```

Sort by score and read the low ones.

✓ You are now looking at a month of your own agent apparently failing 85% of
the time, and nobody knew, because nobody opened this page.

---

## Part C · The judge that could not see

### 9 · Grade the same answer twice

Before believing that number, check the thing that produced it.

```bash
python evals/judge_demo.py
```

One real turn, then the same judge model grading the same answer two ways.

```
QUESTION  What are your wire transfer fees?
ROUTE     policy
RETRIEVED 1704 characters of the bank's own data

  WITHOUT the evidence
    score 3   pass False
    ...specific fee figures without any evidence that these come from
    the bank's actual data...

  WITH the evidence
    score 9   pass True
    ...accurately cited all wire transfer fees from the retrieved
    evidence, invented nothing...
```

✓ Same question, same answer, same judge model. **3, then 9.**

### 10 · See why, in two lines

Open `vendor/buildrbank/orchestration/graph.py` and find the judge node:

```python
v = verdict(state["message"], state.get("reply", ""),
            evidence=state.get("evidence", ""))
```

That last argument is this week's fix. Until it was added, the judge was given
the question and the answer and nothing else, so it could not tell a figure
**quoted** from the handbook apart from one the model **invented** - and its
rubric sends anything specific to the "invents fees, rates, policies" band.

The evidence was already sitting in the state. Nobody was passing it.

> **The better the agent answered, the worse it scored.** An agent that gives
> vague, figure-free answers would have scored higher.

✓ You can explain to someone else why the 3.54 was meaningless.

---

## Part D · A test set

### 11 · Read what a test set looks like

```bash
cat evals/dataset.yaml
```

Ten questions, each with a **reference** - the answer a knowledgeable human
would give. Deliberately mixed, because a test set of easy questions tells you
nothing:

| kind | what it tests |
| --- | --- |
| `fact` | the answer is in the handbook, with exact figures to get wrong |
| `action` | the customer needs something **done**, not explained |
| `refusal` | investment advice, another customer's balance - it must decline |
| `unknown` | the handbook is silent, so it must say so rather than invent |

> **Why a file and not the Langfuse UI.** Week 08 made the server a file so it
> could be reviewed, versioned and rebuilt. This does the same to the
> definition of "correct". Langfuse is the mirror; the repo is the truth.

✓ You can name which of the ten you think the agent will fail.

### 12 · Write two of your own

Add two items to `evals/dataset.yaml`. One `fact` taken from
`scripts/data/bank_handbook.txt`, and one `refusal` or `unknown` of your own
invention.

```yaml
- id: your-id-here
  kind: fact
  question: ...
  reference: >-
    ...
```

This is the actual skill of the week, and it is slower than it looks. Writing
the reference forces you to decide what a complete answer is - whether it
needs the figure, the caveat, the next step, the phone number. Nobody can do
that for you, because it is a decision about your product.

> **Ids must be unique and stable.** They are how an edited reference updates
> an existing item instead of creating a second one.

✓ `python -c "import yaml;print(len(yaml.safe_load(open('evals/dataset.yaml'))))"`
prints 12.

### 13 · Push it to Langfuse

```bash
python evals/push_dataset.py
```

✓ It lists every item, ending with `12 items in dataset 'buildrbank-support'`.

---

## Part E · Run it

### 14 · Grade the agent against your references

```bash
python evals/run_eval.py --name baseline
```

Two to three minutes. It runs each question through the real agent, one at a
time, and grades every answer against the reference you wrote.

```
  item                       score  pass
  --------------------------------------
  wire-fees                   10.0  True
  ...
  lost-card                    4.0  False
  --------------------------------------
  mean 8.70 / 10   passed 9/10
```

The last line is a link to the run in Langfuse. Open it.

✓ You have a number you can defend, because you can point at what produced it.

### 15 · Find the one that failed, and read it

Open the failing item in Langfuse and read the judge's comment. For the stock
dataset that is `lost-card`:

> *"takes action to freeze the card but critically omits providing the 24-hour
> emergency line and fails to mention the mobile app option."*

Ask the question the number cannot answer: **is the agent wrong, or is my
reference wrong?** Both happen. When this dataset was first written the
reference expected a phone number, the agent started freezing the card
instead, and the *reference* was the thing that needed changing.

✓ You have decided which it is, and you can say why.

---

## Part F · Change one thing, and prove it helped

### 16 · Read the prompt that caused it

```bash
grep -A4 '"bb-voice"' vendor/buildrbank/orchestration/prompts.py
```

```
- SHORT: usually one sentence, never more than two.
- Do NOT volunteer costs, fees, or later steps of the procedure
  unless the customer explicitly asked about them
```

The agent was obeying this exactly. Brevity was outranking telling a customer
whose card had just been stolen that a 24-hour line exists. That is not a bug
in the code - it is two requirements colliding, and nobody noticed until a
test wrote the expectation down.

✓ You can point at the line responsible.

### 17 · Publish a new version of the prompt

In Langfuse, open **Prompts** → `bb-voice` → **Edit**. Add an exception
immediately after the "do not volunteer" rule:

```
- EXCEPTION, safety: if the procedure concerns a lost or stolen card,
  fraud, or an unauthorised transaction, ALWAYS include the 24-hour
  emergency line +94 11 234 5000 and that the card can be locked
  immediately in the mobile app.
```

Save it with the **production** label.

> **Notice what you did not do.** No code change. No commit. No deploy. No
> restart. The running app picks up the new prompt on its next fetch, and
> rolling back is moving the `production` label to version 1.

✓ `bb-voice` shows version 2, labelled `production`.

### 18 · Run it again, and compare

```bash
python evals/run_eval.py --name with-safety-carveout
```

```
  lost-card                    7.0  True
  --------------------------------------
  mean 9.00 / 10   passed 10/10
```

Open both runs in Langfuse side by side.

| run | mean | passed | `lost-card` |
| --- | --- | --- | --- |
| `baseline` | 8.70 | 9/10 | 4 · failed |
| `with-safety-carveout` | 9.00 | 10/10 | 7 · passed |

✓ You changed one thing and have evidence that it helped - a number, not an
opinion.

> **Be honest about what this proves.** Between those two runs one unrelated
> item moved from 9 to 7 on a path the prompt never touched. Models are not
> deterministic. Read the aggregate, never a single row, and do not claim a
> win from one run.

---

## What we deliberately left out

So you know these exist:

- **Human feedback** - a thumbs up or down from a real user, written onto the
  same trace as a score. The cheapest signal you will ever get.
- **Online evaluation** - running the judge automatically on a sample of live
  traffic instead of by hand.
- **Regression gates** - failing the pipeline when the mean drops, so a bad
  prompt cannot reach production.
- **Judge calibration** - grading your judge against human verdicts, because
  you have now seen exactly how wrong a judge can be.

None of it changes what you did today. A trace, a reference, and a score you
can defend is the whole story.
