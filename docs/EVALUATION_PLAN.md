# Evaluation Plan

## Benchmark
The starter benchmark contains 24 original synthetic scenarios: 12 Knowledge Agent tasks and 12 Workflow Agent tasks. Eight are marked development and 16 held-out evaluation. The set is deliberately small and results are exploratory.

## Experimental comparison
- **Baseline:** task-focused instructions with the shared approved tool registry.
- **Verified:** adds explicit source retrieval and post-action verification instructions.

Keep model ID, dataset version, tools and other settings fixed. Run matched case IDs under both strategies. Begin with development cases, inspect traces and grader errors, then use held-out cases once the approach is fixed.

## Metrics
### Knowledge tasks
- Required-term coverage.
- Required document retrieval recall.
- Citation coverage.
- Correct abstention on missing information.
- Tool-call precision, recall and F1 (repeated calls count as additional tool calls).

### Workflow tasks
- Task success from actual sandbox postconditions.
- State-match rate.
- Tool-call precision, recall and F1; repeated calls count as additional calls.
- Blocked action attempts and tool errors.
- Sandbox mutations.

### Operational
- End-to-end latency.
- Input/output tokens.
- Estimated API cost only when verified token prices are configured.

## Statistical reporting
Report success rate with a 95% Wilson score interval. For baseline versus verified on matched case IDs, the project includes an exact two-sided McNemar/binomial calculation. With only a few scenarios, treat p-values as exploratory and show raw paired outcomes.

## Grader limitations
Keyword checks may penalise correct paraphrases. Citation presence does not prove entailment. State checks do not fully assess optimality of intermediate steps. Tool F1 counts tool-call occurrences, but does not assess argument-level correctness. Human review is needed for nuanced quality.

## Failure taxonomy
1. Retrieval failure.
2. Wrong or outdated source.
3. Unsupported claim.
4. Missing citation.
5. Tool-selection error.
6. Argument error.
7. Sequence error.
8. Incorrect final state.
9. Attempted disallowed action.
10. Abstention error.

Do not claim statistically significant or general performance gains from the starter benchmark.


## Run configuration and comparison controls

Every live run stores the model identifier, benchmark version and write-approval setting. The dashboard groups results by that configuration and performs paired baseline/verified analysis only within an identical configuration. Do not interpret comparisons across different models, datasets or permissions as a prompt-strategy experiment.
