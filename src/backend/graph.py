import os
from dotenv import load_dotenv, find_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from azure.identity import AzureCliCredential
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel

from .state import IndentState, WorkspaceContext

COLORS = {
    "cyan":     "#00e5ff",
    "purple":   "#bd93f9",
    "green":    "#50fa7b",
    "yellow":   "#f1fa8c",
    "red":      "#ff5555",
    "orange":   "#ffb86c",
    "pink":     "#ff79c6",
    "white":    "#f8f8f2",
    "dim":      "#6272a4",
    "bg_dark":  "#282a36",
    "bg_line":  "#44475a",
    "shadow":   "#333645",
}

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
        "1. An extremely dense and detailed ledger of the project's current state, architectures, and accomplishments (current_state).\n"
        "2. An identification of the libraries, languages, or frameworks being used.\n"
        "3. An educated prediction of what the user is trying to build.\n"
        "4. A structural overview."
    )
    
    result = structured_llm.invoke(prompt)
    return {
        "workspace_context": result,
        "file_list": tree_structure
    }

def check_for_query(state: IndentState) -> str:
    """Routes to END if this is just an initialization pass, else proceeds to query_planner."""
    query = state.get("user_query", "")
    if query and query.strip():
        return "query_planner"
    return END

def query_planner(state: IndentState) -> dict:
    """Drafts an execution plan and asks clarifying questions if requirements are ambiguous."""
    from .state import QueryPlannerOutput
    structured_llm = model.with_structured_output(QueryPlannerOutput, strict=True)
    
    ctx = state.get("workspace_context")
    query = state.get("user_query", "")
    
    current_state_str = ctx.current_state if hasattr(ctx, 'current_state') else (ctx.get("current_state", "No context") if isinstance(ctx, dict) else "No context")
    stack = ctx.tech_stack if hasattr(ctx, 'tech_stack') else (ctx.get("tech_stack", []) if isinstance(ctx, dict) else "No stack")
    
    prompt = (
        "You are the Indent query planner.\n"
        f"Workspace State: {current_state_str}\n"
        f"Tech Stack: {stack}\n\n"
        f"User Query: {query}\n\n"
        "Draft an execution plan. Do not make assumptions about missing architectural details. "
        "If critical decisions are unspecified, leave the plan high-level and output specific clarifying questions."
    )
    
    result = structured_llm.invoke(prompt)
    return {
        "plan": result.plan,
        "questions": result.questions
    }

def check_for_questions(state: IndentState) -> str:
    """Routes to the interrupt node if the planner generated questions, otherwise jumps to approval."""
    questions = state.get("questions", [])
    if questions and len(questions) > 0:
        return "ask_user_questions"
    return "ask_plan_approval"

def ask_user_questions(state: IndentState) -> dict:
    from langgraph.types import interrupt
    user_answers = interrupt({
        "type": "ask_questions",
        "questions": state.get("questions", [])
    })
    return {"answers": user_answers}

def plan_updater(state: IndentState) -> dict:
    from .state import PlanUpdaterOutput
    structured_llm = model.with_structured_output(PlanUpdaterOutput, strict=True)
    
    prompt = (
        "You are the Indent plan updater.\n"
        f"Original Plan: {state.get('plan', '')}\n\n"
        f"Questions asked: {state.get('questions', [])}\n"
        f"User Answers: {state.get('answers', [])}\n\n"
        "Rewrite the plan incorporating the user's architectural decisions."
    )
    result = structured_llm.invoke(prompt)
    return {"plan": result.plan, "questions": [], "answers": []}

def ask_plan_approval(state: IndentState) -> dict:
    from langgraph.types import interrupt
    decision = interrupt({
        "type": "ask_approval",
        "plan": state.get("plan", "")
    })
    return {"is_approved": decision}

def check_approval(state: IndentState) -> str:
    if state.get("is_approved"):
        return "code_generator"
    return "ask_rejection_feedback"

def ask_rejection_feedback(state: IndentState) -> dict:
    from langgraph.types import interrupt
    feedback = interrupt({"type": "ask_feedback"})
    return {"rejection_feedback": feedback}

def alternate_architecture_llm(state: IndentState) -> dict:
    from .state import AlternateArchitectureOutput
    structured_llm = model.with_structured_output(AlternateArchitectureOutput, strict=True)
    
    prompt = (
        "You are the Indent alternate architecture planner.\n"
        f"Original Plan: {state.get('plan', '')}\n\n"
        f"User's Rejection Feedback: {state.get('rejection_feedback', '')}\n\n"
        "Based on the user's feedback, generate specific clarifying questions to determine a new architectural approach."
    )
    result = structured_llm.invoke(prompt)
    return {"questions": result.questions}

def ask_alternate_questions(state: IndentState) -> dict:
    from langgraph.types import interrupt
    user_answers = interrupt({
        "type": "ask_questions",
        "questions": state.get("questions", [])
    })
    return {"answers": user_answers}

def plan_updater_llm(state: IndentState) -> dict:
    from .state import PlanUpdaterOutput
    structured_llm = model.with_structured_output(PlanUpdaterOutput, strict=True)
    
    prompt = (
        "You are the Indent plan updater.\n"
        f"Previous Plan: {state.get('plan', '')}\n\n"
        f"Alternate Questions asked: {state.get('questions', [])}\n"
        f"User Answers: {state.get('answers', [])}\n\n"
        "Rewrite the execution plan incorporating the user's new architectural decisions."
    )
    result = structured_llm.invoke(prompt)
    return {"plan": result.plan, "questions": [], "answers": []}

def ask_revised_plan_approval(state: IndentState) -> dict:
    from langgraph.types import interrupt
    decision = interrupt({
        "type": "ask_approval",
        "plan": state.get("plan", "")
    })
    return {"is_approved": decision}

def check_revised_approval(state: IndentState) -> str:
    if state.get("is_approved"):
        return "code_generator"
    return "reset_state"

def reset_state(state: IndentState) -> dict:
    return {
        "plan": "",
        "questions": [],
        "answers": [],
        "rejection_feedback": "",
        "is_approved": None
    }

def code_generator(state: IndentState) -> dict:
    from .state import CodeGeneratorOutput
    structured_llm = model.with_structured_output(CodeGeneratorOutput, strict=True)
    
    ctx = state.get("workspace_context")
    current_state_str = ctx.current_state if hasattr(ctx, 'current_state') else (ctx.get("current_state", "None") if isinstance(ctx, dict) else "None")
    
    prompt = (
        "You are the Indent Code Generator.\n"
        f"Approved Plan:\n{state.get('plan')}\n\n"
        f"Workspace Context:\n{current_state_str}\n\n"
        "Generate the exact list of file edits needed to implement this plan."
    )
    result = structured_llm.invoke(prompt)
    edits = [edit.model_dump() for edit in result.file_edits]
    return {"file_edits": edits}

def file_writing_agent(state: IndentState) -> dict:
    """Deterministic Python agent that strictly applies the LLM's requested file edits."""
    from rich.console import Console
    console = Console()
    
    edits = state.get("file_edits", [])
    for edit in edits:
        original_path = edit.get("file_path", "")
        action = edit.get("action", "").lower()
        search_block = edit.get("search_block", "")
        replace_block = edit.get("replace_block", "")
        
        safe_path = original_path.lstrip("/\\")
        if safe_path.startswith("." + os.sep) or safe_path.startswith("./"):
            safe_path = safe_path[2:]
            
        abs_path = os.path.abspath(safe_path)
        
        try:
            if action == "new":
                dir_name = os.path.dirname(abs_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(replace_block)
            else:
                if not os.path.exists(abs_path):
                    basename = os.path.basename(safe_path)
                    found = False
                    for root_dir, dirs, files in os.walk("."):
                        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", "__pycache__"]]
                        if basename in files:
                            abs_path = os.path.abspath(os.path.join(root_dir, basename))
                            found = True
                            break
                            
                    if not found:
                        console.print(f"[{COLORS['red']}]Warning: File '{original_path}' does not exist for edit action '{action}'[/{COLORS['red']}]")
                        continue
                    else:
                        rel = os.path.relpath(abs_path)
                        console.print(f"[{COLORS['yellow']}]Note: Auto-resolved '{original_path}' to '{rel}'[/{COLORS['yellow']}]")
                        
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if search_block and search_block not in content:
                    console.print(f"[{COLORS['yellow']}]Warning: Search block not found in {os.path.relpath(abs_path)}. Skipping replacement.[/{COLORS['yellow']}]")
                    continue
                    
                if action == "replace":
                    content = content.replace(search_block, replace_block)
                elif action == "remove":
                    content = content.replace(search_block, "")
                elif action == "add":
                    content = content.replace(search_block, search_block + "\n" + replace_block)
                    
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
        except Exception as e:
            console.print(f"[{COLORS['red']}]Error writing to {original_path}: {e}[/{COLORS['red']}]")
            
    return {}

def incremental_state_updater(state: IndentState) -> dict:
    """Rewrites the current_state string integrating the new file edits."""
    from .state import IncrementalStateOutput
    structured_llm = model.with_structured_output(IncrementalStateOutput, strict=True)
    
    ctx = state.get("workspace_context")
    current_state = ctx.current_state if hasattr(ctx, 'current_state') else (ctx.get("current_state", "No previous state.") if isinstance(ctx, dict) else "No previous state.")
    
    prompt = (
        "You are the Indent State Updater.\n"
        f"Previous State Context:\n{current_state}\n\n"
        f"Executed File Edits:\n{state.get('file_edits', [])}\n\n"
        "Rewrite the dense current_state ledger to completely incorporate these new modifications and the latest architectural reality."
    )
    result = structured_llm.invoke(prompt)
    
    new_ctx = ctx.copy() if isinstance(ctx, dict) else (ctx.model_dump() if hasattr(ctx, 'model_dump') else {})
    new_ctx["current_state"] = result.updated_state
    
    return {
        "workspace_context": new_ctx
    }

def route_start(state: IndentState) -> str:
    """Conditionally bypasses workspace analysis if the user opted to skip it."""
    if state.get("skip_analysis"):
        query = state.get("user_query", "")
        if query and query.strip():
            return "query_planner"
        return END
    return "workspace_analyzer"

def build_graph():
    builder = StateGraph(IndentState)
    
    builder.add_node("workspace_analyzer", workspace_analyzer)
    builder.add_node("query_planner", query_planner)
    builder.add_node("ask_user_questions", ask_user_questions)
    builder.add_node("plan_updater", plan_updater)
    builder.add_node("ask_plan_approval", ask_plan_approval)
    builder.add_node("ask_rejection_feedback", ask_rejection_feedback)
    builder.add_node("alternate_architecture_llm", alternate_architecture_llm)
    builder.add_node("ask_alternate_questions", ask_alternate_questions)
    builder.add_node("plan_updater_llm", plan_updater_llm)
    builder.add_node("ask_revised_plan_approval", ask_revised_plan_approval)
    builder.add_node("reset_state", reset_state)
    builder.add_node("code_generator", code_generator)
    builder.add_node("file_writing_agent", file_writing_agent)
    builder.add_node("incremental_state_updater", incremental_state_updater)
    
    builder.add_conditional_edges(
        START,
        route_start,
        {"workspace_analyzer": "workspace_analyzer", "query_planner": "query_planner", END: END}
    )
    
    builder.add_conditional_edges("workspace_analyzer", check_for_query, {"query_planner": "query_planner", END: END})
    builder.add_conditional_edges("query_planner", check_for_questions, {"ask_user_questions": "ask_user_questions", "ask_plan_approval": "ask_plan_approval"})
    builder.add_edge("ask_user_questions", "plan_updater")
    builder.add_edge("plan_updater", "ask_plan_approval")
    builder.add_conditional_edges("ask_plan_approval", check_approval, {"code_generator": "code_generator", "ask_rejection_feedback": "ask_rejection_feedback"})
    builder.add_edge("ask_rejection_feedback", "alternate_architecture_llm")
    builder.add_edge("alternate_architecture_llm", "ask_alternate_questions")
    builder.add_edge("ask_alternate_questions", "plan_updater_llm")
    builder.add_edge("plan_updater_llm", "ask_revised_plan_approval")
    builder.add_conditional_edges("ask_revised_plan_approval", check_revised_approval, {"code_generator": "code_generator", "reset_state": "reset_state"})
    builder.add_edge("reset_state", END)
    builder.add_edge("code_generator", "file_writing_agent")
    builder.add_edge("file_writing_agent", "incremental_state_updater")
    builder.add_edge("incremental_state_updater", END)
    
    return builder.compile(checkpointer=MemorySaver())

indent_graph = build_graph()
