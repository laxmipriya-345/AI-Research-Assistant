const API = "/api";
let currentSessionId = null;

// ---------- Sessions ----------

async function loadSessions() {
  const res = await fetch(`${API}/sessions`);
  const sessions = await res.json();
  const list = document.getElementById("sessionList");
  list.innerHTML = "";
  sessions.forEach((s) => {
    const el = document.createElement("div");
    el.className = "session-item" + (s.id === currentSessionId ? " active" : "");
    el.textContent = s.title;
    el.onclick = () => selectSession(s.id, s.title);
    list.appendChild(el);
  });
}

async function createSession() {
  const title = prompt("Session title:", "New Research Session") || "New Research Session";
  const res = await fetch(`${API}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const session = await res.json();
  await loadSessions();
  selectSession(session.id, session.title);
}

async function selectSession(id, title) {
  currentSessionId = id;
  document.getElementById("sessionTitle").textContent = title;
  await loadSessions();
  await loadHistory();
  await loadDocuments();
  await loadNotes();
}

// ---------- Chat ----------

async function loadHistory() {
  const chatArea = document.getElementById("chatArea");
  chatArea.innerHTML = "";
  if (!currentSessionId) return;
  const res = await fetch(`${API}/sessions/${currentSessionId}/history`);
  const messages = await res.json();
  messages.forEach((m) => appendMessage(m.role, m.content));
}

function appendMessage(role, content) {
  const chatArea = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
  return div;
}

function appendSteps(steps) {
  if (!steps || steps.length === 0) return;
  const chatArea = document.getElementById("chatArea");
  const div = document.createElement("div");
  div.className = "msg steps";
  div.textContent = steps
    .map((s) => (s.type === "tool_call" ? `→ calling ${s.tool}(${s.detail})` : `← ${s.tool} result received`))
    .join("\n");
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

document.getElementById("chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentSessionId) {
    alert("Create or select a session first.");
    return;
  }
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  appendMessage("user", message);

  const thinking = appendMessage("assistant", "Thinking...");

  const res = await fetch(`${API}/sessions/${currentSessionId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      use_web_search: document.getElementById("toggleWeb").checked,
      use_documents: document.getElementById("toggleDocs").checked,
    }),
  });
  const data = await res.json();
  thinking.remove();
  appendSteps(data.steps);
  appendMessage("assistant", data.answer);
  loadNotes(); // in case the agent saved a note
});

// ---------- Documents ----------

async function loadDocuments() {
  const list = document.getElementById("docList");
  list.innerHTML = "";
  if (!currentSessionId) return;
  const res = await fetch(`${API}/sessions/${currentSessionId}/documents`);
  const docs = await res.json();
  docs.forEach((name) => {
    const el = document.createElement("div");
    el.className = "doc-item";
    el.textContent = name;
    list.appendChild(el);
  });
}

document.getElementById("fileInput").addEventListener("change", async (e) => {
  if (!currentSessionId) {
    alert("Create or select a session first.");
    return;
  }
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  await fetch(`${API}/sessions/${currentSessionId}/documents`, {
    method: "POST",
    body: formData,
  });
  e.target.value = "";
  loadDocuments();
});

// ---------- Notes ----------

async function loadNotes() {
  const list = document.getElementById("notesList");
  list.innerHTML = "";
  if (!currentSessionId) return;
  const res = await fetch(`${API}/sessions/${currentSessionId}/notes`);
  const notes = await res.json();
  notes.forEach((n) => {
    const el = document.createElement("div");
    el.className = "note-item";
    el.innerHTML = `<button class="del-btn" title="Delete">✕</button><div class="note-title">${escapeHtml(n.title)}</div><div>${escapeHtml(n.content)}</div>`;
    el.querySelector(".del-btn").onclick = async () => {
      await fetch(`${API}/sessions/${currentSessionId}/notes/${n.id}`, { method: "DELETE" });
      loadNotes();
    };
    list.appendChild(el);
  });
}

document.getElementById("addNoteBtn").addEventListener("click", async () => {
  if (!currentSessionId) {
    alert("Create or select a session first.");
    return;
  }
  const title = prompt("Note title:");
  if (!title) return;
  const content = prompt("Note content:") || "";
  await fetch(`${API}/sessions/${currentSessionId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content }),
  });
  loadNotes();
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Init ----------

document.getElementById("newSessionBtn").addEventListener("click", createSession);
loadSessions();
