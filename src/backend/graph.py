import os
from dotenv import load_dotenv, find_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from azure.identity import AzureCliCredential
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel

from .state import IndentState, WorkspaceContext

load_dotenv(find_dotenv())

model = AzureAIOpenAIApiChatModel(
    project_endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", ""),
    credential=AzureCliCredential(),
    model="gpt-4.1-mini",
)

import fnmatch

def workspace_analyzer(state: IndentState) -> dict:
    """
    Analyzes the local codebase and updates the workspace context.
    Enforces deterministic output using Pydantic structured output.
    """
    structured_llm = model.with_structured_output(WorkspaceContext, strict=True)
    
    gitignore_patterns = [".git"]  
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.endswith("/"):
                        line = line[:-1]
                    if line.startswith("/"):
                        line = line[1:]
                    gitignore_patterns.append(line)
                    
    items = []
    if os.path.exists("."):
        for item in os.listdir("."):
            ignored = False
            for pattern in gitignore_patterns:
                if fnmatch.fnmatch(item, pattern):
                    ignored = True
                    break
            if not ignored:
                items.append(item)
    
    prompt = (
        "You are 'Indent', an AI workspace analyzer. Please analyze this directory structure "
        "and provide an initial summary of the codebase.\n"
        f"Files and Directories in root: {items}"
    )
    
    result = structured_llm.invoke(prompt)
    
    return {"workspace_context": result}

def build_graph():
    """Builds and compiles the foundational LangGraph state machine."""
    builder = StateGraph(IndentState)
    
    builder.add_node("workspace_analyzer", workspace_analyzer)
    
    builder.add_edge(START, "workspace_analyzer")
    builder.add_edge("workspace_analyzer", END)
    
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

indent_graph = build_graph()
