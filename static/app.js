// Custom Frontend Logic for ET TechGig DevNext '26 ADK + RAG Concierge

let sessionId = null;

const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const resetSessionBtn = document.getElementById("resetSessionBtn");
const kbSectionList = document.getElementById("kbSectionList");

const keyAlertBanner = document.getElementById("keyAlertBanner");
const navKeyDot = document.getElementById("navKeyDot");
const navKeyLabel = document.getElementById("navKeyLabel");
const heroModelBadge = document.getElementById("heroModelBadge");
const ragModeSubtitle = document.getElementById("ragModeSubtitle");

const keyModal = document.getElementById("keyModal");
const openKeyModalBtn = document.getElementById("openKeyModalBtn");
const bannerKeyBtn = document.getElementById("bannerKeyBtn");
const closeKeyModalBtn = document.getElementById("closeKeyModalBtn");
const keyForm = document.getElementById("keyForm");
const apiKeyInput = document.getElementById("apiKeyInput");

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(md) {
  const lines = escapeHtml(md).split("\n");
  let html = "";
  let inUl = false;
  let inOl = false;

  const formatInline = (text) =>
    text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(
        /(https?:\/\/[^\s<)]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
      );

  const closeLists = () => {
    if (inUl) {
      html += "</ul>";
      inUl = false;
    }
    if (inOl) {
      html += "</ol>";
      inOl = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeLists();
      continue;
    }

    const ulMatch = line.match(/^[-*•]\s+(.+)/);
    const olMatch = line.match(/^\d+\.\s+(.+)/);

    if (ulMatch) {
      if (inOl) {
        html += "</ol>";
        inOl = false;
      }
      if (!inUl) {
        html += "<ul>";
        inUl = true;
      }
      html += `<li>${formatInline(ulMatch[1])}</li>`;
    } else if (olMatch) {
      if (inUl) {
        html += "</ul>";
        inUl = false;
      }
      if (!inOl) {
        html += "<ol>";
        inOl = true;
      }
      html += `<li>${formatInline(olMatch[1])}</li>`;
    } else if (line.startsWith("### ")) {
      closeLists();
      html += `<p><strong>${formatInline(line.slice(4))}</strong></p>`;
    } else if (line.startsWith("## ")) {
      closeLists();
      html += `<p><strong>${formatInline(line.slice(3))}</strong></p>`;
    } else {
      closeLists();
      html += `<p>${formatInline(line)}</p>`;
    }
  }

  closeLists();
  return html || `<p>${escapeHtml(md)}</p>`;
}

function appendMessage(role, content, sources = []) {
  const article = document.createElement("article");
  article.className = `msg msg--${role}`;

  const roleLabel = document.createElement("div");
  roleLabel.className = "msg__role";
  roleLabel.textContent = role === "user" ? "// YOU" : "// DEVNEXT ’26 CONCIERGE";

  const bubble = document.createElement("div");
  bubble.className = "msg__bubble";
  if (role === "user") {
    bubble.textContent = content;
  } else {
    bubble.innerHTML = renderMarkdown(content);
  }

  article.appendChild(roleLabel);
  article.appendChild(bubble);

  if (role === "assistant" && Array.isArray(sources) && sources.length > 0) {
    const details = document.createElement("details");
    details.className = "rag-sources";

    const summary = document.createElement("summary");
    const modeLabel = sources[0].mode || "RAG";
    summary.textContent = `Grounded in ${sources.length} DevNext ’26 RAG chunk${sources.length > 1 ? "s" : ""} • ${modeLabel}`;
    details.appendChild(summary);

    const list = document.createElement("div");
    list.className = "rag-sources__items";

    for (const src of sources) {
      const item = document.createElement("div");
      item.className = "rag-source-item";
      item.innerHTML = `
        <div class="rag-source-item__head">
          <span>${escapeHtml(src.section)}</span>
          <span class="rag-source-item__score">score: ${Number(src.score).toFixed(2)}</span>
        </div>
        <div class="rag-source-item__snippet">${escapeHtml(src.snippet)}</div>
      `;
      list.appendChild(item);
    }

    details.appendChild(list);
    article.appendChild(details);
  }

  chatMessages.appendChild(article);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return article;
}

function appendTypingIndicator() {
  const article = document.createElement("article");
  article.className = "msg msg--assistant";
  article.innerHTML = `
    <div class="msg__role">// DEVNEXT ’26 CONCIERGE • RETRIEVING RAG CONTEXT</div>
    <div class="msg__bubble">
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  chatMessages.appendChild(article);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return article;
}

async function sendQuestion(messageText) {
  const text = messageText.trim();
  if (!text) return;

  appendMessage("user", text);
  chatInput.value = "";
  sendBtn.disabled = true;

  const typingNode = appendTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
      }),
    });

    const data = await res.json();
    typingNode.remove();

    if (!res.ok) {
      appendMessage(
        "assistant",
        `**Configuration / API Notice:** ${data.detail || "Unable to reach the ADK agent."}`
      );
      if (res.status === 400) {
        keyModal.classList.remove("hidden");
      }
      return;
    }

    sessionId = data.session_id;
    appendMessage("assistant", data.response, data.sources || []);
  } catch (err) {
    typingNode.remove();
    appendMessage("assistant", "Network error while contacting the local Google ADK server.");
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

async function loadHealthAndCorpus() {
  try {
    const res = await fetch("/api/status");
    const status = await res.json();

    heroModelBadge.textContent = `⚡ ADK Runner • ${status.model}`;
    ragModeSubtitle.textContent = `Google ADK • ${status.rag_chunks} Indexed Sections • ${status.embeddings_ready ? "Hybrid Gemini Vector + BM25" : "BM25 Ready"}`;

    if (status.api_key_configured) {
      navKeyDot.classList.add("ready");
      navKeyLabel.textContent = "API Ready";
      keyAlertBanner.classList.add("hidden");
    } else {
      navKeyDot.classList.remove("ready");
      navKeyLabel.textContent = "Set API Key";
      keyAlertBanner.classList.remove("hidden");
    }

    kbSectionList.innerHTML = "";
    for (const sec of status.sections || []) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "kb-item";
      btn.innerHTML = `<span>${escapeHtml(sec.section)}</span><span class="kb-item__check">↗</span>`;
      btn.addEventListener("click", () => {
        sendQuestion(`Tell me everything about "${sec.section}" at ET TechGig DevNext 2026.`);
      });
      kbSectionList.appendChild(btn);
    }
  } catch (err) {
    kbSectionList.innerHTML = '<div class="kb-loading">Unable to load status.</div>';
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendQuestion(chatInput.value);
});

document.querySelectorAll(".prompt-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.getAttribute("data-prompt");
    if (prompt) sendQuestion(prompt);
  });
});

resetSessionBtn.addEventListener("click", () => {
  sessionId = null;
  chatMessages.innerHTML = "";
  appendMessage(
    "assistant",
    "Started a fresh **Google ADK** session. Ask me any question related to **ET TechGig DevNext ’26**!"
  );
});

openKeyModalBtn.addEventListener("click", () => keyModal.classList.remove("hidden"));
bannerKeyBtn.addEventListener("click", () => keyModal.classList.remove("hidden"));
closeKeyModalBtn.addEventListener("click", () => keyModal.classList.add("hidden"));

keyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = apiKeyInput.value.trim();
  if (!key) return;

  const res = await fetch("/api/configure-key", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key }),
  });

  if (res.ok) {
    apiKeyInput.value = "";
    keyModal.classList.add("hidden");
    await loadHealthAndCorpus();
    appendMessage(
      "assistant",
      "**Gemini API key configured!** `gemini-3.8-flash` and `gemini-embedding-001` hybrid RAG are now active. Ask me anything about **ET TechGig DevNext ’26**."
    );
  }
});

loadHealthAndCorpus();

