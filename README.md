# Indent

**Indent** is a terminal-based AI coding agent. You point it at a codebase, tell it what you want built or changed, and it plans the work with you before touching a single file — asking clarifying questions when your request is ambiguous, showing you the plan before it executes, and only writing code once you've approved it.

It's built on [LangGraph](https://github.com/langchain-ai/langgraph) as a proper state machine (not a single prompt-and-pray loop), runs on Azure AI Foundry, and lives entirely in a styled terminal UI powered by `rich` and `prompt_toolkit`. Sessions aren't throwaway either — you can save your progress on the way out and pick the same conversation back up, with full project context, the next time you launch Indent.

```
Indent > What would you like to build or modify?
❯❯ Add rate limiting to the /api/upload endpoint
```

## Why this exists

Most "AI coding agent" demos either dump code straight into your repo with no review step, or ask a single vague question and then hallucinate the rest of the architecture. Indent is an attempt to fix both problems by treating code generation as a **pipeline with checkpoints**, not a single LLM call:

1. It reads your workspace before it does anything else.
2. It drafts a plan — and explicitly refuses to guess at missing architectural decisions. If something is ambiguous, it asks.
3. It shows you the full plan and waits for your approval.
4. If you reject the plan, it doesn't just retry — it asks *why*, generates a genuinely different architecture, and asks new clarifying questions for that alternative.
5. Only after approval does it generate code, and even then, generation and file-writing are two separate steps: the LLM decides *what* to change, and a deterministic Python agent is the only thing that actually touches your disk.
6. After files are written, a dedicated node folds those changes back into Indent's internal picture of your project, so the next turn — or the next session, days later — starts from an accurate understanding instead of a stale one.

## How it works

Indent is implemented as a LangGraph state graph. Every box below is a real node in the graph, and every diamond is a real conditional edge — this isn't a simplified marketing diagram, it's close to how `src/backend/graph.py` is actually wired.

![Indent workflow diagram](flow.jpeg)

The diagram above shows the core planning/execution loop, which hasn't changed. What's new sits at the two ends of it — how a session *starts* and what happens right after files are written — described below.

Walking through it:

- **Initialization** — On startup, Indent checks the `.indent/` folder for saved sessions. If any exist, you get an arrow-key menu to resume one or start fresh; otherwise it goes straight to asking permission to analyze the workspace. Decline analysis and Indent still starts, just without workspace context (`skip_analysis`) — it isn't an exit condition anymore, only a shortcut.
- **Workspace analyzer (LLM)** — Once permitted, an LLM node walks your directory tree (respecting `.gitignore`), reads file contents up to a context budget, and produces a structured `WorkspaceContext`. This is the field that changed most: instead of a one-line `summary`, it now writes a dense `current_state` ledger — a plain-English account of the project's architecture and current accomplishments, explicitly instructed to contain **no raw code, diffs, or literal file contents**. That ledger is what makes session resume useful — you get your project's story back, not just a stale snippet.
- **Query planner (LLM)** — When you type a request, this node drafts a plan against that `current_state` ledger. Its instructions are explicit: *make no assumptions*. If your request leaves architectural decisions open, it holds the plan at a high level and returns clarifying questions instead of guessing.
- **If Questions → Ask User** — If there are questions, Indent pauses (via LangGraph's `interrupt`) and asks them one at a time in the terminal.
- **Plan updater (LLM)** — Your answers, the original questions, and the draft plan are fed back into an LLM that rewrites the plan to reflect your decisions.
- **Plan shared with user → approval** — The finalized plan is rendered as Markdown in the terminal. You approve or reject it.
  - **Approved** → straight to code generation.
  - **Rejected** → you're asked *why*, and that feedback goes to a separate "alternate architecture" LLM, which proposes a fresh set of clarifying questions rather than patching the old plan. Those get answered, a new plan is generated, and you're asked to approve *that* one. Reject again, and Indent resets its planning state cleanly rather than looping forever.
- **Code generator (LLM)** — Given the approved plan and workspace context, this node returns a strict, structured list of file edits — not raw text, but a typed list of `{file_path, action, search_block, replace_block}` objects, like this:

```json
[
  {
    "file_path": "src/backend/graph.py",
    "action": "replace",
    "search_block": "def chatbot_node(state: State):\n    response = model.invoke(state['messages'])\n    return {'messages': [response]}",
    "replace_block": "def chatbot_node(state: State):\n    # Updated to use structured output\n    response = structured_model.invoke(state['messages'])\n    return {'messages': [response]}"
  }
]
```

- **File writing agent** — This is the one node in the whole graph that isn't an LLM. It's plain, deterministic Python: it walks the list of edits and applies each one (`new`, `replace`, `add`, or `remove`) directly to disk, warning you in the terminal if a `search_block` can't be found rather than silently failing. Separating "decide what to change" from "actually change it" means the model never has unsupervised write access — it can only propose edits in a fixed schema that the agent then applies mechanically. It's also gotten sturdier: paths are normalized before writing, and if the LLM's proposed `file_path` doesn't exist exactly as given, the agent falls back to searching the tree for a matching filename and tells you it auto-resolved the path, instead of just failing.
- **Incremental state updater (LLM)** — New node, runs right after the file writing agent, before `END`. It takes the edits that were just applied and rewrites the `current_state` ledger to reflect them — same rules as before (plain English, no code) — so the workspace context stays accurate turn over turn instead of describing the codebase as it looked at the very first analysis.

Every one of these LLM calls uses **structured output** (via Pydantic schemas in `src/backend/state.py`), so the graph is never parsing free-form text to decide what to do next — every hand-off between nodes is a typed object.

## Session persistence

Indent can save a conversation and pick it back up later — the plan, the workspace's `current_state` ledger, message history, and everything else in the graph's state, not just a transcript.

**Saving:** run `/quit` (or `/exit`) and Indent writes the current session to a JSON file under `.indent/` before exiting.

- `/quit my-feature` saves it as `.indent/my-feature.json`.
- `/quit` with no name asks the model for one: it looks at your last query and generates a short, URL-safe, hyphenated filename (e.g. `add-postgres-database.json`). If that can't be generated for any reason, it falls back to `session.json`.
- If a session was resumed earlier in this run, `/quit` saves back to that same file automatically.
- Name collisions are handled by appending `-1`, `-2`, and so on, so you never silently overwrite a save you didn't explicitly ask to overwrite.
- If you'd rather exit without saving, use `/quit!`, `/exit!`, `/quit-nosave`, `/exit-nosave`, or `/drop`.

**Resuming:** launch Indent in a directory that has a `.indent/` folder with at least one saved session, and instead of the usual permission prompt you'll see a menu:

```
Select a session to resume, or start anew:
  ❯ Start a new chat
    add-postgres-database
    fix-rate-limiter
```

Navigate with the arrow keys (or number keys as a fallback on terminals without raw-mode support) and hit Enter. Pick a saved session and Indent loads its state straight into the graph's checkpointer and prints the project's `current_state` ledger so you can see exactly where things were left off — no permission prompt, no re-analysis, no lost context.

Saved sessions live in `.indent/` inside the analyzed workspace, and that folder is already listed in `.gitignore` — it's local working state, not something you'd commit.

## Tech stack

| Layer | What's used |
|---|---|
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) state graph with an in-memory checkpointer, so a session can pause on `interrupt()` and resume exactly where it left off |
| Model access | [LangChain](https://github.com/langchain-ai/langchain) + `langchain-azure-ai`, talking to **Azure AI Foundry** (`gpt-4.1-mini` by default) via `AzureCliCredential` |
| Structured output | Pydantic models for every LLM node's return type — plans, questions, file edits, workspace context |
| Terminal UI | [`rich`](https://github.com/Textualize/rich) for rendering (live-updating banners, Markdown plans, syntax-highlighted diffs, tables) and [`prompt_toolkit`](https://github.com/prompt-toolkit/python-prompt-toolkit) for the input session (multiline editing, history, slash-command autocomplete) |
| Config | `python-dotenv` for environment variables |

## Getting started

### Prerequisites

- Python 3.10+ (the bundled virtual environment was built against 3.14)
- An Azure AI Foundry project with a deployed chat model, and the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed and logged in (`az login`) — authentication is handled via `AzureCliCredential`, so there's no API key to manage for the model calls themselves
- Git (Indent reads your `.gitignore` to decide what to skip when analyzing a workspace)

### Installation

```bash
git clone https://github.com/Abhay27113234214/Indent.git
cd Indent

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
AZURE_AI_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-name>
```

Then authenticate the Azure CLI so `AzureCliCredential` can pick up your session:

```bash
az login
```

That's the only variable `graph.py` actually reads at import time. Everything else follows Azure AI Foundry's standard project configuration.

### Running it

From the project root, with your virtual environment active:

```bash
python src/main.py
```

On Windows, `indent.bat` does the same thing:

```bash
indent.bat
```

You'll see an animated welcome banner. If `.indent/` already has saved sessions from this workspace, you'll be offered a menu to resume one; otherwise you'll get the permission prompt — Indent won't read a single file in your workspace until you say yes.

## Usage

Once you're past the permission prompt (or you've resumed a saved session), Indent drops you into a prompt loop:

```
What would you like to build or modify?
❯❯ Add a health-check endpoint to the API
```

From there:

- Type a normal request and Indent will plan, ask questions if needed, show you the plan, and wait for approval before writing anything.
- Prefix a line with `!` to run a shell command directly without leaving the session, e.g. `!git status` or `!pytest`.
- Prefix a line with `/` for built-in commands.

### Commands

| Command | What it does |
|---|---|
| `/help` | Shows the command table |
| `/clear` | Clears the screen and replays the welcome banner |
| `/quit [name]`, `/exit [name]` | Saves the session to `.indent/<name>.json` (auto-named by the model if you leave `name` off) and exits |
| `/quit!`, `/exit!`, `/quit-nosave`, `/exit-nosave`, `/drop` | Exits without saving |
| `!<command>` | Runs `<command>` in bash and prints the output inline |

See [Session persistence](#session-persistence) above for the full save/resume flow.

### Editing keybindings

The input box supports multiline prompts: press **Alt+Enter** to insert a newline without submitting, and plain **Enter** to send. Command history is persisted to `~/.indent_history` between sessions.

## Project structure

```
Indent/
├── src/
│   ├── main.py              # Entry point — boots the TUI
│   ├── backend/
│   │   ├── graph.py          # The LangGraph state machine: every node and edge above
│   │   ├── state.py          # Pydantic schemas for state + every structured LLM output
│   │   └── persistence.py    # Saves/loads full session state to .indent/*.json, auto-names sessions via LLM
│   └── tui/
│       ├── app.py            # Main input loop, interrupt handling, command dispatch
│       ├── console.py        # Welcome banner, theme, colors, goodbye screen
│       └── prompt.py         # prompt_toolkit session: history, keybindings, slash-command completion
├── requirements.txt
├── indent.bat                # Windows launcher
└── README.md
```

## Design notes worth knowing

- **The plan can come back empty.** If you reject a revised plan twice, Indent resets `plan`, `questions`, `answers`, and `is_approved` back to a clean slate instead of looping — you'll see a prompt to be more precise on your next request rather than the agent quietly retrying forever.
- **File edits are search-and-replace, not full rewrites.** Every non-`new` edit works against an exact `search_block`. If that block isn't found verbatim in the file (for example, because the file changed since analysis), the writing agent skips that edit and warns you instead of guessing at a fuzzy match.
- **In-process state is checkpointed; cross-session state is explicit.** The graph itself is compiled with an in-memory checkpointer keyed by `thread_id`, which is what makes `interrupt()`/`resume` (the question-and-approval flow) possible without losing state mid-conversation. That checkpoint still doesn't survive a process restart on its own — session persistence across restarts is handled separately, by explicitly dumping the graph's state to `.indent/*.json` on `/quit` and reloading it with `update_state()` on the next launch.
- **The state ledger is deliberately code-free.** Both `workspace_analyzer` and `incremental_state_updater` are explicitly instructed never to include raw code, diffs, or literal file contents in `current_state` — it's meant to stay a compact architectural summary, not a second copy of your codebase, so it stays cheap to keep in context turn after turn.

## Roadmap / known limitations

- The workspace analyzer caps how much file content it reads per pass (a fixed character budget), so very large repositories will be summarized from a partial view rather than the whole codebase.
- Session files are plain JSON on disk with no encryption — treat `.indent/` like any other local file containing your conversation and project details, and keep it out of version control (it's already in `.gitignore`).
- There's currently no automated test suite in this repo; contributions there are especially welcome.

## Contributing

Issues and pull requests are welcome. If you're proposing a change to the graph itself, it's worth sketching the new node/edge structure first — the whole point of this project is that the control flow is explicit and inspectable, and that's easiest to keep true if changes are reviewed at the graph level, not just the code level.

## License

No license has been added to this repository yet. Until one is, treat the code as "all rights reserved" — reach out to the repository owner if you'd like to use it beyond personal reference.