from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class WorkspaceContext(BaseModel):
    """Structured output schema for the workspace_analyzer LLM node."""
    summary: str = Field(description="A brief summary of what the codebase does.")
    tech_stack: list[str] = Field(description="List of detected languages, frameworks, and tools.")
    structure_overview: str = Field(description="A brief overview of the directory structure.")
    project_prediction: str = Field(description="An educated guess on what the user is trying to build or achieve.")

class QueryPlannerOutput(BaseModel):
    """Structured output for the query_planner LLM node."""
    plan: str = Field(description="The proposed execution plan or high-level architecture.")
    questions: list[str] = Field(description="Clarifying questions if the architecture or requirements are ambiguous. Empty list if none.")

class PlanUpdaterOutput(BaseModel):
    """Structured output for the plan_updater LLM node."""
    plan: str = Field(description="The updated execution plan incorporating user answers.")

class AlternateArchitectureOutput(BaseModel):
    """Structured output for the alternate_architecture_llm node."""
    questions: list[str] = Field(description="Clarifying questions for an alternative architecture.")

class IndentState(TypedDict):
    """Core memory schema for the LangGraph state machine."""
    messages: Annotated[list, add_messages]
    workspace_context: WorkspaceContext | None
    file_list: list[str] | None
    user_query: str | None
    plan: str | None
    questions: list[str] | None
    answers: list[str] | None
    rejection_feedback: str | None
    is_approved: bool | None
