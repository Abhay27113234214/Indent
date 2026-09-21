from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class WorkspaceContext(BaseModel):
    """Structured output schema for the workspace_analyzer LLM node."""
    summary: str = Field(description="A brief summary of what the codebase does.")
    tech_stack: list[str] = Field(description="List of detected languages, frameworks, and tools.")
    structure_overview: str = Field(description="A brief overview of the directory structure.")
    project_prediction: str = Field(description="An educated guess on what the user is trying to build or achieve.")

class IndentState(TypedDict):
    """Core memory schema for the LangGraph state machine."""
    messages: Annotated[list, add_messages]
    workspace_context: WorkspaceContext | None
    file_list: list[str] | None
    plan: str | None
    questions: list[str] | None
