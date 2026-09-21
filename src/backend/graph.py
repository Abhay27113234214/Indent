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
    
    gitignore_patterns = [".git", "__pycache__", "node_modules", "venv", ".venv"]  
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.endswith("/"): line = line[:-1]
                    if line.startswith("/"): line = line[1:]
                    gitignore_patterns.append(line)
                    
    tree_structure = []
    file_contents = ""
    
    char_limit = 30000  
    current_chars = 0
    
    if os.path.exists("."):
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in gitignore_patterns)]
            for file in files:
                if any(fnmatch.fnmatch(file, p) for p in gitignore_patterns):
                    continue
                    
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, ".")
                tree_structure.append(rel_path)
                
                if current_chars < char_limit:
                    try:
                        if os.path.getsize(filepath) > 100000:
                            continue
                            
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        snippet = f"\n--- {rel_path} ---\n{content}\n"
                        
                        if current_chars + len(snippet) > char_limit:
                            allowed = char_limit - current_chars
                            snippet = snippet[:allowed] + "\n...[TRUNCATED DUE TO CONTEXT LIMIT]...\n"
                            
                        file_contents += snippet
                        current_chars += len(snippet)
                    except Exception:
                        pass
                        
    prompt = (
        "You are 'Indent', an AI workspace analyzer. Please analyze the following codebase.\n\n"
        f"Directory Structure:\n{', '.join(tree_structure)}\n\n"
        f"File Contents:\n{file_contents}\n"
        "Based on this information, please provide:\n"
        "1. An initial summary of the codebase.\n"
        "2. An identification of the libraries, languages, or frameworks being used.\n"
        "3. An educated prediction of what the user is trying to build."
    )
    
    result = structured_llm.invoke(prompt)
    return {
        "workspace_context": result,
        "file_list": tree_structure
    }

def build_graph():
    """Builds and compiles the foundational LangGraph state machine."""
    builder = StateGraph(IndentState)
    
    builder.add_node("workspace_analyzer", workspace_analyzer)
    
    builder.add_edge(START, "workspace_analyzer")
    builder.add_edge("workspace_analyzer", END)
    
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

indent_graph = build_graph()
