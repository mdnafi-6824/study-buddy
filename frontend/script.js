// Study Buddy - front-end chat logic
// Talks to the FastAPI backend at /api/chat and keeps the UI in sync
// with the session-based conversation the server maintains.

const API_BASE = window.STUDY_BUDDY_API_BASE || "http://localhost:8000";

const messagesEl = document.getElementById("messages");
const typingRow = document.getElementById("typingRow");
const form = document.getElementById("composerForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");
const quickBtn = document.getElementById("quickBtn");
const chips = document.getElementById("chips");

let sessionId = localStorage.getItem("studybuddy_session") || null;

function addMessage(text, sender) {
  const row = document.createElement("div");
  row.className = `msg ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${sender === "bot" ? "bot-avatar" : ""}`;
  if (sender === "bot") avatar.textContent = "🎓";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (sender === "bot") {
    // Render minimal markdown (bold) and strip anything else the model
    // might still emit (headers, list dashes) so it never shows raw
    // markdown symbols in the chat bubble. Escape HTML first to stay safe.
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    let clean = escaped
      .replace(/^#{1,6}\s*/gm, "")          // strip leading ###/## headers
      .replace(/^\s*[-*]\s+/gm, "");        // strip leading list dashes/bullets
    clean = clean.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); // keep real bold
    clean = clean.replace(/\*(.+?)\*/g, "$1"); // drop leftover single asterisks
    bubble.innerHTML = clean.replace(/\n/g, "<br>");
  } else {
    bubble.textContent = text;
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(isLoading) {
  typingRow.hidden = !isLoading;
  sendBtn.disabled = isLoading;
  if (isLoading) messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(text) {
  addMessage(text, "user");
  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }

    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem("studybuddy_session", sessionId);
    addMessage(data.reply, "bot");
  } catch (err) {
    addMessage(
      `Sorry, something went wrong: ${err.message}. Check that the backend is running and your API key is set.`,
      "bot"
    );
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendMessage(text);
});

resetBtn.addEventListener("click", () => {
  sessionId = null;
  localStorage.removeItem("studybuddy_session");
  messagesEl.innerHTML = "";
  addMessage(
    "New conversation started! What would you like to study?",
    "bot"
  );
});

quickBtn.addEventListener("click", () => {
  chips.hidden = !chips.hidden;
});

chips.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  input.value = btn.dataset.prompt + " ";
  input.focus();
  chips.hidden = true;
});
