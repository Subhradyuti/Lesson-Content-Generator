"""
LangGraph workflow graph assembly.
Compiles the stateful graph with all nodes and conditional edges.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.workflow.nodes import (
    node_build_revision_instructions,
    node_create_lesson_plan,
    node_decide_next_action,
    node_evaluate_lesson,
    node_finalize_run,
    node_generate_lesson,
    node_persist_results,
    node_return_result,
    node_validate_evaluation,
    node_validate_request,
)
from app.workflow.routing import (
    route_after_build_revision,
    route_after_decide,
    route_after_evaluate,
    route_after_finalize,
    route_after_generate,
    route_after_persist,
    route_after_plan,
    route_after_validate,
    route_after_validate_evaluation,
)
from app.workflow.state import WorkflowState


@lru_cache(maxsize=1)
def build_workflow():
    """Build and compile the LangGraph workflow. Cached for reuse."""
    graph = StateGraph(WorkflowState)

    # ── Register nodes ────────────────────────────────────────────────────
    graph.add_node("validate_request", node_validate_request)
    graph.add_node("create_lesson_plan", node_create_lesson_plan)
    graph.add_node("generate_lesson", node_generate_lesson)
    graph.add_node("evaluate_lesson", node_evaluate_lesson)
    graph.add_node("validate_evaluation", node_validate_evaluation)
    graph.add_node("decide_next_action", node_decide_next_action)
    graph.add_node("build_revision_instructions", node_build_revision_instructions)
    graph.add_node("finalize_run", node_finalize_run)
    graph.add_node("persist_results", node_persist_results)
    graph.add_node("return_result", node_return_result)

    # ── Entry point ───────────────────────────────────────────────────────
    graph.add_edge(START, "validate_request")

    # ── Conditional edges ─────────────────────────────────────────────────
    graph.add_conditional_edges(
        "validate_request",
        route_after_validate,
        {
            "create_lesson_plan": "create_lesson_plan",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "create_lesson_plan",
        route_after_plan,
        {
            "generate_lesson": "generate_lesson",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "generate_lesson",
        route_after_generate,
        {
            "evaluate_lesson": "evaluate_lesson",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "evaluate_lesson",
        route_after_evaluate,
        {
            "validate_evaluation": "validate_evaluation",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "validate_evaluation",
        route_after_validate_evaluation,
        {
            "decide_next_action": "decide_next_action",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "decide_next_action",
        route_after_decide,
        {
            "finalize_run": "finalize_run",
            "build_revision_instructions": "build_revision_instructions",
        },
    )

    graph.add_conditional_edges(
        "build_revision_instructions",
        route_after_build_revision,
        {
            "generate_lesson": "generate_lesson",
            "finalize_run": "finalize_run",
        },
    )

    graph.add_conditional_edges(
        "finalize_run",
        route_after_finalize,
        {
            "persist_results": "persist_results",
        },
    )

    graph.add_conditional_edges(
        "persist_results",
        route_after_persist,
        {
            "return_result": "return_result",
        },
    )

    # ── Terminal node ─────────────────────────────────────────────────────
    graph.add_edge("return_result", END)

    return graph.compile()


def run_workflow(initial_state: dict) -> WorkflowState:
    """
    Execute the compiled workflow with the given initial state.
    Returns the final state after all nodes have executed.
    """
    workflow = build_workflow()
    final_state = workflow.invoke(initial_state)
    return final_state
