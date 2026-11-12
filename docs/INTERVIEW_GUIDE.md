# WorkflowBench: Interview Preparation Notes

## 30-second explanation

WorkflowBench is a small research platform for testing AI agents on two kinds of tasks: evidence-backed information retrieval and bounded multi-step workflow execution. It provides a local tool environment, records observable execution traces, compares a baseline instruction strategy with a verify-after-action strategy, and grades outcomes using deterministic checks.

## Why build it?

A plausible final answer does not prove that an agent completed the correct workflow. A model might retrieve the wrong record, call a tool with the wrong parameters or claim an action succeeded when it did not. WorkflowBench compares the final answer with evidence and, for workflow tasks, the actual state of a sandbox database.

## Why two agents?

They represent two different capabilities while sharing the same execution infrastructure:

- The Knowledge Agent is read-only and must cite the documents it retrieves.
- The Workflow Agent can perform bounded local actions such as creating tasks, updating a record status and drafting a message.

The two tracks share instructions, schemas, trace structures and sandbox controls. Provider-specific runners handle the API protocol, while separate tool allowlists keep each agent's capabilities explicit.

## Explain the tool-calling loop

1. The selected provider adapter sends the task and JSON-schema tool definitions to its model endpoint: Responses API for OpenAI, Chat Completions for Gemini and Ollama.
2. The model may return a function call containing a tool name and arguments.
3. The application parses the arguments and checks the tool allowlist and write permission.
4. The local Python function executes inside the sandbox.
5. The application returns the tool output using the matching call ID.
6. The model continues until it returns a final answer or reaches the tool-call limit.

The model requests tools; the application owns and executes the actual Python functions. The dashboard requires a write-approval checkbox, the single-case CLI uses --allow-writes, and matched workflow comparisons also require explicit --allow-writes approval.

## Why use strict schemas?

Strict schemas reduce malformed tool arguments and constrain the shape of function-call inputs. They do not replace application-side permission checks, resource checks or business rules. The sandbox remains responsible for rejecting unavailable tools, invalid records and unsafe state transitions.

## Why not use LangGraph or another agent framework?

The v0.2 objective is learnability and transparency. A short explicit loop is enough for two agents with a small tool set. A framework may become useful if the workflow grows to include long-running state, complex branching, retries, resumability or many handoffs.

## Why is the evaluator deterministic?

Deterministic checks are inspectable and repeatable. The Knowledge Agent is checked for required terms, retrieved sources, citations and abstention. The Workflow Agent is checked against the actual sandbox state. These graders are deliberately narrow: they do not fully judge writing quality or semantic entailment, so human review remains necessary.

## What is a trace?

A trace is the chronological record of visible execution events: tool requested, tool result, blocked call, error and final response. It helps identify where a workflow failed. It does not contain or attempt to evaluate hidden model chain-of-thought.

## How are workflow tasks graded?

The evaluator checks the tools used and compares the final sandbox state with expected postconditions. For example, it verifies that the requested task exists with the correct title, owner, due date and related record ID. A correct-sounding final response is not enough if the task was not created.

## How do you evaluate improvement?

Use the same held-out case IDs, model and tool permissions under baseline and verified strategies. Compare task success and other metrics. The Wilson interval communicates uncertainty in a binomial success rate. The exact McNemar test compares paired binary outcomes on matched case IDs. The initial benchmark is small, so all results are exploratory.

## What are the biggest limitations?

1. Only 24 synthetic cases are included in v0.2.
2. Keyword search is not a production retrieval system.
3. Phrase checks can miss correct paraphrases and reward keyword copying.
4. Citation presence does not prove that a claim is entailed by the source.
5. The workflow grader checks state but does not fully grade the optimality of intermediate steps.
6. Tool-call F1 counts repeated calls but does not assess argument-level correctness.
7. Real API cost requires verified provider prices.

## Questions to practise

- What is the difference between tool calling and an agent framework?
- Why do you need both schema validation and application-level authorization?
- How would you improve the benchmark from 24 to 200 cases?
- How would you measure grader agreement with human reviewers?
- Why might verification improve success but increase latency and cost?
- How would you make a write operation idempotent?
- How would you test prompt injection in retrieved documents?
- What would you change before using this with real customer data?

Answer in your own words and point to the exact module that implements each feature.


## Why store model, dataset and write settings?

A strategy comparison is only meaningful when the other conditions are held constant. WorkflowBench records the model ID, benchmark version and write-approval setting for each run. The dashboard only pairs baseline and verified runs with matching settings, avoiding a misleading comparison between runs that had different tool permissions or used different model versions.
