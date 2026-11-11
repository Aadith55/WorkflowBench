# Research Notes

## Research question
How do explicit verification instructions and application-level tool controls affect task completion, tool-use quality, groundedness, safety and operating cost in two small classes of AI workflows?

## Methodological references
- [OpenAI function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI agent evaluation guide](https://developers.openai.com/api/docs/guides/agent-evals)
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [AgentBench paper](https://arxiv.org/abs/2308.03688)

These inform the methodology. The starter tasks in WorkflowBench are original synthetic examples, not reproduced external benchmark cases.

## Hypotheses
- H1: explicit verification may improve postcondition success on multi-step tasks.
- H2: source retrieval and citation instructions may improve citation coverage.
- H3: verification may increase latency and token use; success must be assessed alongside cost.
- H4: application-level permission checks can block disallowed state changes even if the model requests them.

These are hypotheses, not measured results.

## Future commercial research
Once the prototype is working, compare LangSmith, Braintrust, Langfuse and Arize Phoenix using current product pages and pricing. Compare user segment, trace support, evaluation workflow, integrations, governance, pricing and differentiation. Do not infer market share or traction from marketing claims alone.

## Limitations
The benchmark is small and synthetic. Retrieval uses keyword matching. Human review is required for subjective quality. Provider pricing changes, so cost calculations require verified current price inputs.
