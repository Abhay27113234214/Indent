import os
import json
import re
from pydantic import BaseModel, Field
from langchain_core.messages import messages_to_dict, messages_from_dict
from .graph import model

class TitleOutput(BaseModel):
    title: str = Field(description="A short, url-safe hyphenated filename (e.g., add-postgres-database).")

def save_session_to_json(state: dict, save_dir: str = ".indent", custom_filename: str = None, overwrite: bool = False) -> str:
    """Deterministically dumps the active LangGraph state to a JSON file in the given directory."""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
        
    if custom_filename:
        filename = custom_filename.lower().strip()
        filename = re.sub(r'[^a-z0-9\-]', '', filename)
        if not filename:
            filename = "session"
    else:
        query = state.get("user_query")
        if not query:
            filename = "session"
        else:
            structured_llm = model.with_structured_output(TitleOutput, strict=True)
            prompt = f"Generate a short, url-safe hyphenated filename describing this query: '{query}'. Output ONLY the hyphenated name without extension."
            
            try:
                result = structured_llm.invoke(prompt)
                filename = result.title.lower().strip()
                filename = re.sub(r'[^a-z0-9\-]', '', filename)
                if not filename:
                    filename = "session"
            except Exception:
                filename = "session"
                
    if not overwrite:
        base_filename = filename
        counter = 1
        while os.path.exists(os.path.join(save_dir, f"{filename}.json")):
            filename = f"{base_filename}-{counter}"
            counter += 1
        
    filepath = os.path.join(save_dir, f"{filename}.json")
    
    state_copy = state.copy()
    
    if "messages" in state_copy and state_copy["messages"]:
        state_copy["messages"] = messages_to_dict(state_copy["messages"])
        
    def json_default(obj):
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        return str(obj)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state_copy, f, default=json_default, indent=2)
        
    return filepath

def load_session_from_json(filepath: str) -> dict:
    """Reads and returns the state dictionary from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if "messages" in data and data["messages"]:
        data["messages"] = messages_from_dict(data["messages"])
        
    return data
