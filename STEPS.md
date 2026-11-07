# Is it any good? — the whole thing, step by step

**The repository:** <https://github.com/darshaka-weerasinghe/buildrbank-eval>

Twenty steps. By the end you will have put a turn of your own through the
agent and found it in the recording, added a line of instrumentation and
watched a new box appear because of it, worked out what one answer costs,
found out that your agent has been scoring 3.5 out of 10 for a month,
established that the agent was not the problem, written down what "correct"
means for ten questions, and proved that a change you made actually helped.

> **Copy commands from [this file on GitHub](https://github.com/darshaka-weerasinghe/buildrbank-eval/blob/main/STEPS.md),
> not from the PDF handout.** The handout's font joins `--` and `//` into one
> character when you copy it, which breaks `--name` and `https://` in ways the
> error message disguises.

**What this costs.** No servers this week - everything runs on your laptop.
What it does cost is model calls: 3 or 4 live turns in Part B, roughly 3 for
the judge demo, and about 30 for each full evaluation run, of which you will
run three. Budget a few US dollars of OpenRouter credit. Step 4 is about
exactly that, and it is not optional.

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

### 7 · Send one of your own, and give it a name

So far you have been reading traces somebody else caused. Make one.

```bash
python scripts/say.py "What is the fee for a wire transfer?" --session YOURNAME-01
```

Use your actual name, so you can find it again in a room full of people
running the same command. The script prints the reply and the session it
filed the turn under.

Now send a second message to the **same** session:

```bash
python scripts/say.py "And how long does the international one take?" --session YOURNAME-01
```

You never said what "the international one" was. It answered anyway, because
`--session` is doing two jobs at once: it is the thread the agent remembers
between messages, *and* it is the name Langfuse files the trace under. One
name, both halves.

In Langfuse open **Sessions** and find `YOURNAME-01`. Two traces, in order,
the way the customer would have lived through them. That is the difference
between a trace and a session: one turn, versus the conversation it was part
of.

✓ Your session holds two traces, and the second reply answers a question you
only asked half of.

### 8 · Add one line, and watch a new box appear

Nothing in that tree is automatic. Every box is there because somebody put a
decorator on a function. Here is the proof.

Open `vendor/buildrbank/memory/short_term.py`. `append_turns` writes the
transcript to Supabase on every single turn, and it is the one step in the
write path with nothing recording it. Add the import at the top, and one line
directly above the function:

```python
from ..observability import observe
```

```python
@observe()
def append_turns(user_id: str, session_id: str, user_text: str, bot_text: str) -> None:
```

Now send another message, under a new session name:

```bash
python scripts/say.py "What is the daily ATM withdrawal limit?" --session YOURNAME-02
```

Open that trace and look inside `memory_write`. There is an `append_turns`
box in it that did not exist five minutes ago — nineteen boxes where your
last trace had eighteen.

> **That is the entire trick.** There is no such thing as an agent that is
> "observable" and another that is not. There is code with a decorator on it
> and code without, and you have just moved one function from the second pile
> to the first. Everything in Part B exists because someone did this
> thirty-odd times.

✓ `append_turns` appears inside `memory_write` in your newest trace, and not
in the one before it.

### 9 · Work out what a turn costs

Click any `GENERATION` in that trace. Two facts are recorded on it: which
model ran, and how many tokens it used, in and out. For one policy question:

```
router              anthropic/claude-haiku-4.5      420 in     9 out
answer_policy       anthropic/claude-sonnet-4.6     750 in    64 out
```

Two models for one question — a cheap one to decide the route, an expensive
one to write the answer. Your numbers will differ; use your own.

A third call also ran this turn: the judge. It has no token row, because it
is recorded as an *evaluator* rather than a *generation*, and only
generations carry usage. Worth knowing before you quote a monthly figure to
anybody - the easiest way to undercount is to count only the calls somebody
remembered to label.

Now notice what is **missing**: the cost column is empty. Langfuse works out
money by looking the model name up in a price table, and our names reach it
with an OpenRouter prefix on the front — `anthropic/claude-sonnet-4.6`, not
`claude-sonnet-4.6` — which is not a name it knows. So nobody is adding this
up for you.

Do it by hand, once. Open [openrouter.ai/models](https://openrouter.ai/models),
find the two models, and take the per-million-token prices:

```
(input tokens  ÷ 1,000,000) × input price
          +
(output tokens ÷ 1,000,000) × output price
```

That is one question. Now multiply by three questions per customer, a hundred
customers, thirty days.

> **The point is not the number.** It is that a dashboard only knows what you
> told it. Somebody renamed a model to make it work through OpenRouter, the
> money column quietly stopped counting, and every graph still looked fine.
> You will not find that by watching the dashboard. You find it by asking the
> dashboard a question you already know the answer to.

While you are in there, look at what a trace *holds*. It keeps **everything
the model saw** — the customer's words, their account, whatever you retrieved
about them. Open `vendor/buildrbank/observability.py`:

```python
_ACC_RE = re.compile(r"ACC-\d{4,}")
# runs on every traced input and output, before upload
```

Account numbers are masked on your machine, before anything leaves it.

✓ You can say what one answer costs, and you can find a masked
`[REDACTED-ACCOUNT]` in a trace.

### 10 · Find the scores

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

### 11 · Grade the same answer twice

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

### 12 · See why, in two lines

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

### 13 · Read what a test set looks like

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

### 14 · Write two of your own

Open `evals/dataset.yaml` and scroll to the bottom. You are adding two more
questions: one `fact`, whose answer is in the handbook, and one `unknown`,
which the handbook says nothing about.

> **Copy the two blocks below from [STEPS.md on GitHub](https://github.com/darshaka-weerasinghe/buildrbank-eval/blob/main/STEPS.md),
> not from this PDF.** Copying out of a PDF brings the grey box's own indent
> along with the text, so every line lands two spaces too far in and the file
> stops parsing. This is the most common way this step goes wrong.

**The fact one.** Open `scripts/data/bank_handbook.txt` and find a line with a
number in it that none of the ten items has used yet. Here is one, from the
credit card section:

```
BuildrBank Gold. Mid-tier card. Annual fee LKR 5,000, waived for annual
spend above LKR 500,000.
```

Copy this to the end of `dataset.yaml`, then change the words - not the shape:

```yaml
- id: gold-card-fee
  kind: fact
  question: What is the annual fee on the Gold credit card?
  reference: >-
    LKR 5,000 a year, waived if the customer spends more than LKR 500,000
    on the card in a year.
```

**The unknown one.** Now think of something a customer would reasonably ask
that the handbook does not answer. The agent has to say so rather than guess:

```yaml
- id: account-for-a-child
  kind: unknown
  question: Can I open a savings account for my 10-year-old daughter?
  reference: >-
    The handbook does not cover accounts for children, so the agent must say
    it does not know and offer to pass the customer to a person. It must not
    invent an age limit or a product name.
```

**What goes in a reference.** Not the wording - the judge compares meaning,
not phrasing. What it looks for is whether the answer has:

- the **figure**, when there is one
- the **condition** attached to it, when there is one - the waiver above
- what the customer should **do next**, when there is anything to do

**What breaks the file.** YAML counts spaces:

- each item begins with `- id:` hard against the left margin, and the three
  lines under it are indented by exactly two spaces
- `>-` means "the paragraph below, joined into one line". Its text is indented
  four spaces
- spaces only, never tabs

This is the real skill of the week, and it is slower than it looks. Writing
the reference is where you decide what a complete answer is. Nobody can do
that for you, because it is a decision about your product and not about the
code.

> **Ids must be unique and stable.** The id is how an edited reference updates
> the item that already exists instead of creating a second one. Pick a short
> name and then leave it alone.

Count what you have:

```bash
python -c "import yaml;print(len(yaml.safe_load(open('evals/dataset.yaml'))))"
```

> **If that prints a long error** ending in something like
> `mapping values are not allowed here ... line 128, column 9`, it is the
> indentation - and **the line it names is usually fine**. Look at the line
> *above* it. YAML works out where an item begins from its first key, so a
> `kind:` indented deeper than its own `- id:` is not read as a key at all;
> it gets swallowed into the line before, and the error lands on the colon
> that follows. Check that the three lines under `- id:` are indented by
> exactly two spaces, and the text under `>-` by four.

✓ It prints `12`.

### 15 · Push it to Langfuse

```bash
python evals/push_dataset.py
```

✓ It lists every item, ending with `12 items in dataset 'buildrbank-support'`.

---

## Part E · Run it

### 16 · Grade the agent against your references

```bash
python evals/run_eval.py --name baseline
```

Two to three minutes. It runs each question through the real agent, one at a
time, and grades every answer against the reference you wrote.

Note it reads the dataset from **Langfuse**, not from the file - so it runs
the twelve items you pushed in step 15, including your two.

```
  item                       score  pass
  --------------------------------------
  wire-fees                   10.0  True
  ...
  lost-card                    4.0  False
  --------------------------------------
  mean 8.70 / 10   passed 9/10
```

> **That sample is the stock ten items, on prompt version 1.** Yours will say
> `12`, your own two will be in the list, and the numbers will not match -
> different questions, different references, and the models are not
> deterministic. What you are after is the shape: a mean, and a list you can
> sort by score.

The last line is a link to the run in Langfuse. Open it.

✓ You have a number you can defend, because you can point at what produced it.

### 17 · Find the one that failed, and read it

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

### 18 · Read the prompt that caused it

Two rules inside the `bb-voice` prompt did this. Pull them both out:

```bash
grep -n -E 'SHORT:|Do NOT volunteer' vendor/buildrbank/orchestration/prompts.py
```

```
65:        "- SHORT: usually one sentence, never more than two. Say only what is new.\n"
73:        "- Do NOT volunteer costs, fees, or later steps of the procedure unless the "
```

They look like that because the prompt is built up as a Python string, one
quoted line at a time. Open the file at line 65 to read it as prose, or run
`grep -A20 '"bb-voice"' vendor/buildrbank/orchestration/prompts.py` to see the
whole prompt these two lines sit in.

The agent was obeying this exactly. Brevity was outranking telling a customer
whose card had just been stolen that a 24-hour line exists. That is not a bug
in the code - it is two requirements colliding, and nobody noticed until a
test wrote the expectation down.

✓ You can point at the line responsible.

### 19 · Publish a new version of the prompt

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

### 20 · Run it again, and compare

```bash
python evals/run_eval.py --name with-safety-carveout
```

```
  lost-card                    7.0  True
  --------------------------------------
  mean 9.00 / 10   passed 10/10
```

Open both runs in Langfuse side by side. Again, these two runs are the stock
ten items; with your twelve the totals will be different. The row that matters
is `lost-card`, and the direction it moved:

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
