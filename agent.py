"""
Multi-step Reasoning Agent
----------------------------
Orchestrates a tool-use loop against the Anthropic Messages API. The
model can call web_search, search_documents, and save_note as many
times as it needs (up to MAX_REASONING_STEPS) before producing a final
answer, giving it genuine multi-step research capability.
"""
import json
import anthropic

from config import ANTHROPIC_API_KEY, MODEL_NAME, MAX_TOKENS, MAX_REASONING_STEPS
import memory
import documents
import notes as notes_store
from web_search import web_search as run_web_search

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else anthropic.Anthropic()

SYSTEM_PROMPT = """You are an AI Research Assistant. You help the user research topics thoroughly by:
- Searching the web for current, relevant information when needed.
- Searching any documents the user has uploaded to this session.
- Reasoning step by step across multiple tool calls before answering.
- Saving important findings as research notes when the user would benefit from a persistent record.

Guidelines:
- Only call tools when they would actually improve your answer; don't call a tool just because it exists.
- When you use web search or document search results, cite the source (URL or filename) in your answer.
- Be concise but thorough. Prefer structured answers (short paragraphs or bullet points) for research findings.
- If document search and web search disagree, note the discrepancy rather than silently picking one.
"""

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the live web for current information, facts, news, or sources on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_documents",
        "description": "Search the documents the user has uploaded to this session for relevant passages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for within the uploaded documents."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_note",
        "description": "Save an important research finding as a persistent note for the user, tied to this session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the note."},
                "content": {"type": "string", "description": "The note content / finding."},
            },
            "required": ["title", "content"],
        },
    },
]


def _run_tool(session_id: str, tool_name: str, tool_input: dict) -> str:
    if tool_name == "web_search":
        results = run_web_search(tool_input["query"])
        return json.dumps(results, indent=2)

    if tool_name == "search_documents":
        results = documents.search_documents(session_id, tool_input["query"])
        if not results:
            return "No relevant document content found (or no documents uploaded)."
        return json.dumps(results, indent=2)

    if tool_name == "save_note":
        note = notes_store.add_note(session_id, tool_input["title"], tool_input["content"])
        return f"Note saved with id {note['id']}."

    return f"Unknown tool: {tool_name}"


def _summarize_for_memory(existing_summary: str, old_text: str) -> str:
    """Used by memory.maybe_summarize to compress old turns into a running summary."""
    prompt = (
        "Compress the following conversation excerpt into a concise running summary "
        "that preserves key facts, decisions, and findings. Merge it with the existing "
        "summary below.\n\n"
        f"EXISTING SUMMARY:\n{existing_summary or '(none yet)'}\n\n"
        f"NEW EXCERPT:\n{old_text}\n\n"
        "Return only the updated summary text."
    )
    resp = client.messages.create(
        model=MODEL_NAME,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def chat(session_id: str, user_message: str, use_web_search: bool = True, use_documents: bool = True):
    """
    Runs the full multi-step reasoning loop for one user turn.
    Returns (answer_text, steps) where steps is a list of dicts describing
    each tool call made along the way (useful for showing the user the
    agent's research trail).
    """
    memory.add_message(session_id, "user", user_message)

    summary = memory.get_summary(session_id)
    history = memory.get_recent_messages_for_prompt(session_id)

    system = SYSTEM_PROMPT
    if summary:
        system += f"\n\nSummary of earlier conversation in this session:\n{summary}"

    active_tools = [
        t for t in TOOLS
        if (t["name"] != "web_search" or use_web_search)
        and (t["name"] != "search_documents" or use_documents)
    ]

    messages = list(history)
    steps = []

    for _ in range(MAX_REASONING_STEPS):
        resp = client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=active_tools,
            messages=messages,
        )

        tool_calls = [b for b in resp.content if b.type == "tool_use"]

        if not tool_calls:
            final_text = "".join(b.text for b in resp.content if b.type == "text").strip()
            memory.add_message(session_id, "assistant", final_text)
            memory.maybe_summarize(session_id, _summarize_for_memory)
            return final_text, steps

        # Record assistant turn (including tool_use blocks) then execute tools
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        for call in tool_calls:
            steps.append({"type": "tool_call", "tool": call.name, "detail": json.dumps(call.input)})
            result_text = _run_tool(session_id, call.name, call.input)
            steps.append({"type": "tool_result", "tool": call.name, "detail": result_text[:500]})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})

    # Safety valve: ran out of reasoning steps, force a final answer
    resp = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        system=system + "\n\nYou must answer now with what you have; no more tool calls.",
        messages=messages,
    )
    final_text = "".join(b.text for b in resp.content if b.type == "text").strip()
    memory.add_message(session_id, "assistant", final_text)
    memory.maybe_summarize(session_id, _summarize_for_memory)
    return final_text, steps
