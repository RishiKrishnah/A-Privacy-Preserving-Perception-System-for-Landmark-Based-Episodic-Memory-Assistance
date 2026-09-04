// The website talks only to the server.
// Keep this URL pointed at the backend; never put the Gemini API key here.
const API_BASE =
  window.API_BASE ||
  "https://a-privacy-preserving-perception-system.onrender.com/api";

const $ = (id) => document.getElementById(id);

function renderMemories(memories) {
  if (!memories.length) {
    $("memories").innerHTML = "<p>No semantic memories found.</p>";
    return;
  }

  $("memories").innerHTML = memories
    .map(
      (m) => `
    <article class="memory">
      <div class="time">${escapeHtml(m.timestamp || "")}</div>
      <strong>${escapeHtml(m.subject || "Unknown")} → ${escapeHtml(m.action || "")}</strong>
      <div class="meta">
        ${m.landmark ? "Landmark: " + escapeHtml(m.landmark) : ""}
        ${m.details ? " · " + escapeHtml(m.details) : ""}
      </div>
    </article>
  `,
    )
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function refreshMemories() {
  try {
    const res = await fetch(`${API_BASE}/memories/recent?limit=20`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not load memories");
    renderMemories(data.memories || []);
  } catch (err) {
    $("memories").textContent = "Unable to load memories: " + err.message;
  }
}

async function checkStatus() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    $("status").textContent = res.ok ? "● Server connected" : "Server error";
  } catch {
    $("status").textContent = "● Server unavailable";
  }
}

$("queryForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = $("question").value.trim();
  if (!question) return;

  $("answer").classList.remove("hidden");
  $("answer").textContent = "Searching semantic memory…";

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Query failed");

    $("answer").textContent = data.answer;
  } catch (err) {
    $("answer").textContent = "Error: " + err.message;
  }
});

$("refresh").addEventListener("click", refreshMemories);
checkStatus();
refreshMemories();
