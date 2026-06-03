# Trigger evals

`trigger-eval.json` is a set of realistic user queries labelled `should_trigger`
(true/false), used to measure and optimize how reliably the skill's `description`
fires. It mixes clear positives, recurring-digest requests, and tricky **near-misses**
that share keywords with the skill but should *not* trigger it (updating instead of
briefing, summarizing the user's own changelog, other products, how-to/debugging).

## Current description (manually tuned)

The shipped `description` in `../SKILL.md` was hand-tuned for coverage + precision:
it lists natural phrasings ("what's new in Claude", "is my claude-code out of date?",
"what can the API do now?") and includes an explicit "do NOT use it to…" clause to
suppress the near-misses above.

## Running the automated optimizer (optional, more rigorous)

Anthropic's `skill-creator` skill ships a description optimizer that splits these
queries into train/test, measures the real trigger rate (3 runs per query), proposes
improved descriptions, and keeps the best by held-out test score. It needs the
`claude` CLI authenticated (it calls `claude -p` under the hood), so run it on your
own machine rather than in a sandbox:

```bash
# from inside the skill-creator skill directory
python -m scripts.run_loop \
  --eval-set /path/to/claude-release-radar/evals/trigger-eval.json \
  --skill-path /path/to/claude-release-radar \
  --model <your-model-id> \
  --max-iterations 5 \
  --verbose
```

Take the `best_description` it reports and paste it into `../SKILL.md`'s frontmatter
if it beats the current one. Add fresh near-misses here whenever you notice the skill
over- or under-triggering in real use.
