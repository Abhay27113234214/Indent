from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class WorkspaceContext(BaseModel):
    """Structured output schema for the workspace_analyzer LLM node."""
    current_state: str = Field(description="Detailed architectural ledger of the project's state and accomplishments, written in plain English without any raw code snippets.")
    tech_stack: list[str] = Field(description="List of detected languages, frameworks, and tools.")
    structure_overview: str = Field(description="A brief overview of the directory structure.")
    project_prediction: str = Field(description="An educated guess on what the user is trying to build or achieve.")

class IncrementalStateOutput(BaseModel):
    """Structured output for the incremental_state_updater node."""
    updated_state: str = Field(description="The rewritten current_state string integrating the new file edits, in plain English with absolutely NO code snippets.")

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

class FileEdit(BaseModel):
    """A specific file edit operation."""
    file_path: str = Field(description="The relative path to the file.")
    action: str = Field(description="The action to perform: 'new', 'replace', 'add', 'remove'")
    search_block: str = Field(description="The exact text to find in the file. Empty if 'new'.")
    replace_block: str = Field(description="The exact text to replace it with. Empty if 'remove'.")

class CodeGeneratorOutput(BaseModel):
    """Structured output for the code_generator LLM node."""
    file_edits: list[FileEdit] = Field(description="List of file edits to execute the approved plan.")

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
    file_edits: list[dict] | None
    skip_analysis: bool | None
