"""CPython differential mechanism probe for smolagents PR #3001.

Scope: direct reconstruction of evaluate_with's context lifetime algorithm,
not an import or execution of smolagents' full native test suite.

The nested unwind routine mirrors the live PR-head contract. Its oracle is
actual CPython's multi-item `with`, not a second implementation of the same
unwind code. Only ordinary exceptions are compared (agent-specific
FinalAnswerException deliberately differs from Python exception suppression).
"""
from __future__ import annotations
import json
import itertools
import sys
from pathlib import Path


def run_case(n, suppress_mask, phase, failure_index, emulate):
    events = []
    class TestError(RuntimeError):
        pass
    class Context:
        def __init__(self, index):
            self.index = index
        def __enter__(self):
            events.append(('enter', self.index))
            if phase == 'enter' and self.index == failure_index:
                raise TestError('enter-'+str(self.index))
            return self
        def __exit__(self, exc_type, exc, tb):
            events.append(('exit', self.index, exc_type.__name__ if exc_type else None))
            if phase in ('exit', 'body_exit') and self.index == failure_index:
                raise TestError('exit-'+str(self.index))
            return bool(suppress_mask & (1 << self.index))
    def mk(index):
        events.append(('expr', index))
        if phase == 'expr' and index == failure_index:
            raise TestError('expr-'+str(index))
        return Context(index)
    def body():
        events.append(('body',))
        if phase in ('body', 'body_exit'):
            raise TestError('body')
    if emulate:
        contexts = []
        def unwind_contexts(exc_info):
            # Exact algorithmic semantics of live PR #3001, without the
            # intentional FinalAnswerException special-case.
            for context in reversed(contexts):
                try:
                    suppressed = context.__exit__(*exc_info)
                    if suppressed:
                        exc_info = (None, None, None)
                except BaseException as exit_exc:
                    exc_info = (type(exit_exc), exit_exc, exit_exc.__traceback__)
            if exc_info[1] is not None:
                raise exc_info[1].with_traceback(exc_info[2])
        def execute():
            try:
                for i in range(n):
                    ctx = mk(i)
                    entered = ctx.__enter__()
                    contexts.append(ctx)
                body()
            except BaseException as e:
                unwind_contexts((type(e), e, e.__traceback__))
            else:
                unwind_contexts((None, None, None))
    else:
        # Python compiles multi-item with statements to nested context lifetimes.
        # Source is deterministic and contains no user-controlled data.
        code = f"with {', '.join('mk('+str(i)+')' for i in range(n))}:\n    body()\n"
        def execute():
            exec(code, {'mk': mk, 'body': body})
    error = None
    try:
        execute()
    except BaseException as exc:
        error = (type(exc).__name__, str(exc))
    return {'events': events, 'error': error}


def main():
    cases = []
    for n in (2,3,4):
        for mask in range(1 << n):
            cases.append((n,mask,'none',0))
            cases.append((n,mask,'body',0))
            for phase in ('expr','enter','exit','body_exit'):
                for i in range(n):
                    cases.append((n,mask,phase,i))
    results = []
    for params in cases:
        actual = run_case(*params, emulate=False)
        candidate = run_case(*params, emulate=True)
        if actual != candidate:
            results.append({'parameters': params, 'cpython': actual, 'candidate': candidate})
    receipt = {'python': sys.version.split()[0], 'cases': len(cases),
               'exact_trace_and_exception_matches': len(cases)-len(results),
               'mismatches': results[:5], 'mismatch_count': len(results),
               'scope': 'CPython differential ordinary-exception context-lifetime mechanism; not native smolagents run'}
    Path(__file__).with_name('context_unwind_cpython_differential_20261026_results.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    if results:
        raise AssertionError('CPython differential failure!')

if __name__=='__main__':
    main()
