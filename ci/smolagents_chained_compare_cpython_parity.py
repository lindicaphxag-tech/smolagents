"""Native CPython-reference chained comparison acceptance control.

Unlike the production PR, this script does not modify any library code.
It observes __bool__ evaluation counts of custom rich comparison results
through CPython's eval and smolagents' evaluate_python_code.
"""
from smolagents.default_tools import BASE_PYTHON_TOOLS
from smolagents.local_python_executor import evaluate_python_code


def run_case(expr, maker):
    cp_state, cp_events = maker()
    py_result = eval(expr, {}, cp_state)
    sm_state, sm_events = maker()
    smolagents_result, _ = evaluate_python_code(
        "result = " + expr, BASE_PYTHON_TOOLS.copy(), state=sm_state)
    assert py_result is cp_state["final"] or py_result is cp_state["mid"],(expr,py_result)
    assert smolagents_result.output is sm_state["result"]
    assert (sm_state["result"] is sm_state["final"]) == (py_result is cp_state["final"])
    assert (sm_state["result"] is sm_state["mid"]) == (py_result is cp_state["mid"])
    assert sm_events == cp_events,{"expr":expr,"smolagents":sm_events,"CPython":cp_events}
    print("CPYTHON_PARITY",expr,sm_events,flush=True)


def make(final_truth_testing=False,mid_false=False):
    events=[]
    class Return:
        def __init__(self,label):
            self.label=label
        def __bool__(self):
            events.append("bool:"+self.label)
            if self.label=="final" and final_truth_testing:
                raise AssertionError("final rich comparison value must not be bool-tested")
            return self.label!="mid" or not mid_false
    mid=Return("mid")
    final=Return("final")
    class Operand:
        def __init__(self,label):
            self.label=label
        def __lt__(self,other):
            events.append("lt:"+self.label)
            return mid if self.label=="left" else final
    state={"left":Operand("left"),"middle":Operand("middle"),
           "right":Operand("right"),"final":final,"mid":mid}
    return state,events


if __name__=="__main__":
    run_case("left < middle",lambda:make(final_truth_testing=True))
    run_case("left < middle < right",lambda:make(final_truth_testing=True))
    run_case("left < middle < right",lambda:make(mid_false=True))
    print("NATIVE_CP_COMPARE_PARITY_PASSED",flush=True)
