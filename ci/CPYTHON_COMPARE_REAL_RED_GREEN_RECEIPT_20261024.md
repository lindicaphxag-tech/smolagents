# smolagents #3000 merge-acceptance: standalone source-exact CPython counterexample

**2026-10-24 independent local CPU execution, Python 3.13.** This is an isolated *source-exact* test of the `evaluate_condition` method from official [huggingface/smolagents#3000 head `e30facf`](https://github.com/huggingface/smolagents/pull/3000), **not a full smolagents pytest/CI run**.

The complete production method body was copied unchanged from `src/smolagents/local_python_executor.py`. Only the unrelated `evaluate_ast` dependency was replaced with a minimal AST Name-to-object lookup, so rich comparison and truth-testing code remained production-identical. Each observed event trace was compared with literal CPython `eval` of the same expression, using distinct but structurally equivalent custom objects.

Four tested contexts, all passing:

| Expression | Custom rich comparison behavior | Observed CPython & patched `evaluate_condition` side effects |
|---|---|---|
| `a < b` | final object raises if `__bool__` is called | `['lt:a']` |
| `a < b < c` | truthy intermediate; final raises if truth-tested | `['lt:a','bool:mid','lt:b']` |
| `a < b < c` | false-like intermediate | `['lt:a','bool:mid']` (later comparison not executed) |
| `a < b < c < d` | three comparisons, intermediate truth-tested | `['lt:a','bool:mid','lt:b','bool:final','lt:c']` |

Legacy version from the official diff was also executed with the same two-comparator witness: its side-effect trace was `['lt:a','lt:b','bool:mid']`, whereas CPython's expected trace was `['lt:a','bool:mid','lt:b']`. The unpatched code therefore **fails** the semantic-order witness, even when rich comparison results are truthy.

```
PASS source-exact PR #3000 a < b ['lt:a']
PASS source-exact PR #3000 a < b < c ['lt:a', 'bool:mid', 'lt:b']
PASS source-exact PR #3000 a < b < c ['lt:a', 'bool:mid']
PASS source-exact PR #3000 a < b < c < d ['lt:a', 'bool:mid', 'lt:b', 'bool:final', 'lt:c']
PASS old implementation violates CPython comparison side effect trace ['lt:a', 'lt:b', 'bool:mid']
ALL FOUR PATCHED CASES GREEN; LEGACY NEGATIVE CONTROL RED
```

This test does **not** claim to cover the full Python language, all AST nodes, full package import or official HF native Actions, which currently require upstream authorization (`action_required`). The author's other PR-validation branches [#3](https://github.com/lindicaphxag-tech/smolagents/pull/3) and [#4](https://github.com/lindicaphxag-tech/smolagents/pull/4) contain independent native test workflow definitions but have not produced verified successful Actions records in this environment. No upstream comment/reviewer-request was sent because the GitHub integration returns HTTP 403 for those endpoints.

Reviewer-ready takeaway: the exact reviewer-reported extra truth-testing side effect is repaired on the current official head, source-equivalent CPython event-order control is green for all four pre-specified cases, and the old code fails the same control. Remaining gates are **authorized upstream Actions** and a fresh **human review**, rather than unsupported new scope.
