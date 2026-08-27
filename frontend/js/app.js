// Sentinel MA — main UI controller.
// Talks to the backend exclusively through Api (js/api.js) over HTTP.

const state = {
  conversationId: null,
  pendingImageFile: null,
  isRecording: false,
  isSending: false,
  // messageId -> { audioEl, toggleBtn, stopBtn } — lets us pause/resume/stop
  // playback without ever re-fetching audio, and lets a new message's
  // playback cleanly stop whatever was playing before.
  audioRegistry: new Map(),
  currentReview: null,
  selectedDecision: null,
};

const el = {
  chatScroll: document.getElementById("chatScroll"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  micBtn: document.getElementById("micBtn"),
  imageUploadBtn: document.getElementById("imageUploadBtn"),
  imageUploadInput: document.getElementById("imageUploadInput"),
  conversationList: document.getElementById("conversationList"),
  conversationTitle: document.getElementById("conversationTitle"),
  reviewList: document.getElementById("reviewList"),
  reviewCount: document.getElementById("reviewCount"),
  attachmentPreview: document.getElementById("attachmentPreview"),
  attachmentThumb: document.getElementById("attachmentThumb"),
  attachmentName: document.getElementById("attachmentName"),
  removeAttachmentBtn: document.getElementById("removeAttachmentBtn"),
  newConversationBtn: document.getElementById("newConversationBtn"),
  messageTemplate: document.getElementById("messageTemplate"),
  backendStatusDot: document.getElementById("backendStatusDot"),
  backendStatusText: document.getElementById("backendStatusText"),
  // review modal
  reviewModalOverlay: document.getElementById("reviewModalOverlay"),
  reviewModalCloseBtn: document.getElementById("reviewModalCloseBtn"),
  reviewModalAgentTag: document.getElementById("reviewModalAgentTag"),
  reviewModalConfidenceFill: document.getElementById("reviewModalConfidenceFill"),
  reviewModalConfidenceValue: document.getElementById("reviewModalConfidenceValue"),
  reviewModalContent: document.getElementById("reviewModalContent"),
  reviewerNameInput: document.getElementById("reviewerNameInput"),
  decisionApproveBtn: document.getElementById("decisionApproveBtn"),
  decisionEditBtn: document.getElementById("decisionEditBtn"),
  decisionRejectBtn: document.getElementById("decisionRejectBtn"),
  correctedContentField: document.getElementById("correctedContentField"),
  correctedContentInput: document.getElementById("correctedContentInput"),
  reviewNotesInput: document.getElementById("reviewNotesInput"),
  reviewCancelBtn: document.getElementById("reviewCancelBtn"),
  reviewSubmitBtn: document.getElementById("reviewSubmitBtn"),
};

/* ----------------------------- init ----------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  refreshConversations();
  refreshPendingReviews();
  setInterval(refreshPendingReviews, 20000);

  el.messageInput.addEventListener("input", autoGrowTextarea);
  el.messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  el.sendBtn.addEventListener("click", handleSend);
  el.newConversationBtn.addEventListener("click", startNewConversation);
  el.imageUploadBtn.addEventListener("click", () => el.imageUploadInput.click());
  el.imageUploadInput.addEventListener("change", handleImageSelected);
  el.removeAttachmentBtn.addEventListener("click", clearAttachment);
  el.micBtn.addEventListener("click", handleMicClick);

  el.reviewModalCloseBtn.addEventListener("click", closeReviewModal);
  el.reviewCancelBtn.addEventListener("click", closeReviewModal);
  el.reviewModalOverlay.addEventListener("click", (e) => {
    if (e.target === el.reviewModalOverlay) closeReviewModal();
  });
  el.decisionApproveBtn.addEventListener("click", () => selectDecision("approved"));
  el.decisionEditBtn.addEventListener("click", () => selectDecision("edited"));
  el.decisionRejectBtn.addEventListener("click", () => selectDecision("rejected"));
  el.reviewSubmitBtn.addEventListener("click", submitReview);

  wireWelcomeChips();
});

function autoGrowTextarea() {
  el.messageInput.style.height = "auto";
  el.messageInput.style.height = Math.min(el.messageInput.scrollHeight, 140) + "px";
}

function wireWelcomeChips() {
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      el.messageInput.value = chip.dataset.suggest;
      autoGrowTextarea();
      el.messageInput.focus();
    });
  });
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/health`);
    if (!res.ok) throw new Error();
    el.backendStatusDot.className = "status-dot status-dot--ok";
    el.backendStatusText.textContent = "Backend connected";
  } catch {
    el.backendStatusDot.className = "status-dot status-dot--down";
    el.backendStatusText.textContent = "Backend unreachable";
  }
}

function buildMediaUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_CONFIG.BASE_URL}${path}`;
}

/* ------------------------- conversations ------------------------- */

function startNewConversation() {
  stopAllAudio();
  state.conversationId = null;
  el.conversationTitle.textContent = "New consultation";
  el.chatScroll.innerHTML = `
    <div class="welcome-card">
      <h2>Welcome, clinician.</h2>
      <p>Ask a clinical question or upload a medical image for analysis. Questions are answered from
      a pre-loaded PubMed knowledge base, with any non-relevant results automatically backfilled by
      live web search — every response is routed through confidence-based agent handoff and safety
      guardrails, with imaging findings always queued for human sign-off.</p>
      <div class="welcome-card__chips">
        <button class="chip" data-suggest="What are the first-line treatment options for community-acquired pneumonia in adults?">First-line CAP treatment?</button>
        <button class="chip" data-suggest="What is the latest research on GLP-1 receptor agonists for cardiovascular risk reduction?">Latest GLP-1 CV research?</button>
        <button class="chip" data-suggest="Summarize the drug interactions of warfarin with common antibiotics.">Warfarin drug interactions?</button>
      </div>
    </div>`;
  wireWelcomeChips();
  clearAttachment();
  document.querySelectorAll(".conversation-item.active").forEach((n) => n.classList.remove("active"));
}

async function refreshConversations() {
  try {
    const convs = await Api.listConversations();
    el.conversationList.innerHTML = "";
    if (!convs.length) {
      el.conversationList.innerHTML = `<li class="empty-hint">No consultations yet</li>`;
      return;
    }
    convs.forEach((c) => {
      const li = document.createElement("li");
      li.className = "conversation-item" + (c.id === state.conversationId ? " active" : "");
      li.textContent = c.title || "Untitled consultation";
      li.addEventListener("click", () => loadConversation(c.id, c.title));
      el.conversationList.appendChild(li);
    });
  } catch (e) {
    console.error("Failed to load conversations", e);
  }
}

async function loadConversation(id, title) {
  stopAllAudio();
  state.conversationId = id;
  el.conversationTitle.textContent = title || "Consultation";
  el.chatScroll.innerHTML = "";
  document.querySelectorAll(".conversation-item").forEach((n) => n.classList.toggle("active", n.textContent === title));
  try {
    const messages = await Api.getConversationMessages(id);
    messages.forEach((m) => {
      renderMessage({
        messageId: m.id,
        role: m.role,
        content: m.content,
        agentUsed: m.agent_used,
        confidence: m.confidence,
        needsReview: m.needs_human_review,
        sources: (m.sources && m.sources.items) || [],
        imagePreviewUrl: buildMediaUrl(m.image_url),
      });
    });
    scrollToBottom();
  } catch (e) {
    console.error("Failed to load conversation messages", e);
  }
}

/* ------------------------- image attachment ------------------------- */

function handleImageSelected(e) {
  const file = e.target.files[0];
  if (!file) return;
  state.pendingImageFile = file;
  el.attachmentThumb.src = URL.createObjectURL(file);
  el.attachmentName.textContent = file.name;
  el.attachmentPreview.hidden = false;
  el.messageInput.placeholder = "Describe what to analyze in this image (e.g. 'classify this chest X-ray')…";
  el.messageInput.focus();
}

function clearAttachment() {
  state.pendingImageFile = null;
  el.attachmentPreview.hidden = true;
  el.imageUploadInput.value = "";
  el.messageInput.placeholder = "Ask a clinical question, or describe what to analyze in the attached image…";
}

/* ----------------------------- chat ----------------------------- */

async function handleSend() {
  const text = el.messageInput.value.trim();
  if (!text || state.isSending) return;

  state.isSending = true;
  el.sendBtn.disabled = true;

  const imageFile = state.pendingImageFile;
  const localImagePreview = imageFile ? URL.createObjectURL(imageFile) : null;
  renderMessage({ role: "user", content: text, imagePreviewUrl: localImagePreview });
  el.messageInput.value = "";
  autoGrowTextarea();
  scrollToBottom();

  const typingNode = renderTypingIndicator();

  try {
    if (imageFile) {
      const res = await Api.uploadImage(imageFile, text, state.conversationId);
      state.conversationId = res.conversation_id;
      if (el.conversationTitle.textContent === "New consultation") {
        el.conversationTitle.textContent = text.slice(0, 60);
        refreshConversations();
      }
      typingNode.remove();
      renderMessage({
        messageId: res.message_id,
        role: "assistant",
        content: res.findings,
        agentUsed: "image_analysis",
        confidence: res.confidence,
        needsReview: true,
        sources: [],
      });
      clearAttachment();
      scrollToBottom();
      refreshPendingReviews();
      return;
    }

    const res = await Api.sendChatMessage({
      conversationId: state.conversationId,
      message: text,
    });

    state.conversationId = res.conversation_id;
    if (el.conversationTitle.textContent === "New consultation") {
      el.conversationTitle.textContent = text.slice(0, 60);
      refreshConversations();
    }

    typingNode.remove();
    renderMessage({
      messageId: res.message_id,
      role: "assistant",
      content: res.answer,
      agentUsed: res.agent_used,
      confidence: res.confidence,
      needsReview: res.needs_human_review,
      sources: res.sources || [],
    });
    scrollToBottom();
    if (res.needs_human_review) refreshPendingReviews();
  } catch (err) {
    typingNode.remove();
    renderMessage({ role: "assistant", content: `⚠️ ${err.message}`, agentUsed: "error", confidence: 0, needsReview: false, sources: [] });
    scrollToBottom();
  } finally {
    state.isSending = false;
    el.sendBtn.disabled = false;
  }
}

function renderTypingIndicator() {
  const node = document.createElement("article");
  node.className = "message";
  node.innerHTML = `
    <div class="message__avatar">${ICONS.assistant}</div>
    <div class="message__body">
      <div class="message__meta"><span class="message__role">Assistant</span></div>
      <div class="message__content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
    </div>`;
  el.chatScroll.appendChild(node);
  scrollToBottom();
  return node;
}

function renderMessage({ messageId, role, content, agentUsed, confidence, needsReview, sources, imagePreviewUrl }) {
  const frag = el.messageTemplate.content.cloneNode(true);
  const article = frag.querySelector(".message");
  article.classList.add(role === "user" ? "message--user" : "message--assistant");
  if (messageId) article.dataset.messageId = messageId;

  frag.querySelector(".message__avatar").innerHTML = role === "user" ? ICONS.user : ICONS.assistant;
  frag.querySelector(".message__role").textContent = role === "user" ? "You" : "Sentinel MA";

  if (agentUsed) {
    const tag = frag.querySelector(".message__agent-tag");
    tag.textContent = formatAgentLabel(agentUsed);
    tag.hidden = false;
  }

  if (needsReview) {
    frag.querySelector(".message__review-tag").hidden = false;
  }

  const contentEl = frag.querySelector(".message__content");
  let contentHtml = escapeHtml(content).replace(/\n/g, "<br>");
  if (imagePreviewUrl) {
    contentHtml = `<img class="message-image" src="${imagePreviewUrl}" alt="Medical image" />` + contentHtml;
  }
  contentEl.innerHTML = contentHtml;

  if (sources && sources.length) {
    const sourcesEl = frag.querySelector(".message__sources");
    sourcesEl.hidden = false;
    const ul = sourcesEl.querySelector("ul");
    sources.forEach((s) => {
      const li = document.createElement("li");
      const pageInfo = s.page ? ` (p.${s.page})` : "";
      li.innerHTML = `<b>${escapeHtml(s.document)}</b>${pageInfo} — ${escapeHtml((s.snippet || "").slice(0, 160))}${s.snippet && s.snippet.length > 160 ? "…" : ""}`;
      ul.appendChild(li);
    });
  }

  if (role === "assistant" && typeof confidence === "number") {
    const meter = frag.querySelector(".confidence-meter");
    meter.hidden = false;
    const pct = Math.round(confidence * 100);
    const fill = meter.querySelector(".confidence-meter__fill");
    fill.style.width = `${pct}%`;
    fill.classList.toggle("low", pct < 40);
    fill.classList.toggle("mid", pct >= 40 && pct < 70);
    meter.querySelector(".confidence-meter__value").textContent = `${pct}%`;
  }

  const audioControls = frag.querySelector(".audio-controls");
  if (role === "user" || !messageId) {
    audioControls.remove();
  } else {
    const toggleBtn = audioControls.querySelector(".audio-toggle-btn");
    const stopBtn = audioControls.querySelector(".audio-stop-btn");
    toggleBtn.addEventListener("click", () => handleAudioToggle(messageId, content, toggleBtn, stopBtn));
    stopBtn.addEventListener("click", () => handleAudioStop(messageId));
  }

  el.chatScroll.appendChild(frag);
}

function formatAgentLabel(agent) {
  const map = {
    rag: "Knowledge base",
    "rag+web_backfill": "Knowledge base + web backfill",
    web_search: "Web research",
    "rag+web_search_handoff": "RAG → Web handoff",
    image_analysis: "MedGemma imaging",
    general: "General",
    guardrail_blocked: "Blocked",
    error: "Error",
  };
  return map[agent] || agent;
}

function scrollToBottom() {
  el.chatScroll.scrollTop = el.chatScroll.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

/* ----------------------------- voice input ----------------------------- */

async function handleMicClick() {
  if (!VoiceRecorder.isSupported()) {
    alert("Voice recording is not supported in this browser.");
    return;
  }
  const micIcon = el.micBtn.querySelector(".mic-icon-mic");
  const stopIcon = el.micBtn.querySelector(".mic-icon-stop");

  if (!state.isRecording) {
    try {
      await VoiceRecorder.start();
      state.isRecording = true;
      el.micBtn.classList.add("recording");
      micIcon.hidden = true;
      stopIcon.hidden = false;
    } catch (e) {
      alert("Microphone access was denied or is unavailable.");
    }
  } else {
    el.micBtn.classList.remove("recording");
    micIcon.hidden = false;
    stopIcon.hidden = true;
    state.isRecording = false;
    try {
      const blob = await VoiceRecorder.stop();
      el.messageInput.placeholder = "Transcribing…";
      const { text } = await Api.speechToText(blob);
      el.messageInput.value = (el.messageInput.value ? el.messageInput.value + " " : "") + text;
      autoGrowTextarea();
      el.messageInput.focus();
    } catch (e) {
      alert(`Transcription failed: ${e.message}`);
    } finally {
      el.messageInput.placeholder = "Ask a clinical question, or describe what to analyze in the attached image…";
    }
  }
}

/* ----------------------- text-to-speech playback ----------------------- */
// Audio is fetched EXACTLY ONCE per message and cached in that message's own
// <audio> element. Every click after the first only ever calls .play()/
// .pause() on the already-fetched element — never re-invokes the TTS API.

function setAudioButtonVisual(toggleBtn, uiState) {
  const playIcon = toggleBtn.querySelector(".audio-icon-play");
  const pauseIcon = toggleBtn.querySelector(".audio-icon-pause");
  const loadingIcon = toggleBtn.querySelector(".audio-icon-loading");
  playIcon.hidden = uiState === "playing" || uiState === "loading";
  pauseIcon.hidden = uiState !== "playing";
  loadingIcon.hidden = uiState !== "loading";
  toggleBtn.classList.toggle("is-playing", uiState === "playing");
}

function stopAllAudio() {
  state.audioRegistry.forEach((entry, id) => resetAudioEntry(id));
}

function resetAudioEntry(messageId) {
  const entry = state.audioRegistry.get(messageId);
  if (!entry) return;
  entry.audioEl.pause();
  entry.audioEl.currentTime = 0;
  setAudioButtonVisual(entry.toggleBtn, "idle");
  entry.stopBtn.hidden = true;
}

async function handleAudioToggle(messageId, text, toggleBtn, stopBtn) {
  let entry = state.audioRegistry.get(messageId);

  if (!entry) {
    setAudioButtonVisual(toggleBtn, "loading");
    try {
      const blob = await Api.textToSpeech(text);
      const url = URL.createObjectURL(blob);
      const audioEl = new Audio(url);
      audioEl.addEventListener("ended", () => resetAudioEntry(messageId));
      entry = { audioEl, toggleBtn, stopBtn };
      state.audioRegistry.set(messageId, entry);
    } catch (e) {
      setAudioButtonVisual(toggleBtn, "idle");
      alert(`Text-to-speech failed: ${e.message}`);
      return;
    }
  }

  if (entry.audioEl.paused) {
    // Only one message plays at a time — cleanly stop any other before starting this one.
    state.audioRegistry.forEach((_, id) => {
      if (id !== messageId) resetAudioEntry(id);
    });
    await entry.audioEl.play();
    setAudioButtonVisual(toggleBtn, "playing");
    stopBtn.hidden = false;
  } else {
    entry.audioEl.pause();
    setAudioButtonVisual(toggleBtn, "idle");
    // stop button stays visible — there's playback progress to reset via it
  }
}

function handleAudioStop(messageId) {
  resetAudioEntry(messageId);
}

/* --------------------------- human review --------------------------- */

async function refreshPendingReviews() {
  try {
    const reviews = await Api.listPendingReviews();
    el.reviewCount.textContent = reviews.length;
    el.reviewList.innerHTML = "";
    if (!reviews.length) {
      el.reviewList.innerHTML = `<li class="empty-hint">Nothing awaiting review</li>`;
      return;
    }
    reviews.forEach((r) => {
      const li = document.createElement("li");
      li.className = "review-item";
      li.innerHTML = `
        <span class="review-item__snippet">${escapeHtml(r.content.slice(0, 140))}</span>
        <span class="review-item__meta">${formatAgentLabel(r.agent_used)} · ${Math.round(r.confidence * 100)}%</span>`;
      li.addEventListener("click", () => openReviewModal(r));
      el.reviewList.appendChild(li);
    });
  } catch (e) {
    console.error("Failed to load pending reviews", e);
  }
}

function openReviewModal(review) {
  state.currentReview = review;
  state.selectedDecision = null;

  el.reviewModalAgentTag.textContent = formatAgentLabel(review.agent_used);
  const pct = Math.round((review.confidence || 0) * 100);
  el.reviewModalConfidenceFill.style.width = `${pct}%`;
  el.reviewModalConfidenceFill.classList.toggle("low", pct < 40);
  el.reviewModalConfidenceFill.classList.toggle("mid", pct >= 40 && pct < 70);
  el.reviewModalConfidenceValue.textContent = `${pct}%`;
  el.reviewModalContent.textContent = review.content;

  el.correctedContentInput.value = review.content;
  el.correctedContentField.hidden = true;
  el.reviewNotesInput.value = "";
  [el.decisionApproveBtn, el.decisionEditBtn, el.decisionRejectBtn].forEach((b) => b.classList.remove("is-active"));

  el.reviewModalOverlay.hidden = false;
  el.reviewerNameInput.focus();
}

function closeReviewModal() {
  el.reviewModalOverlay.hidden = true;
  state.currentReview = null;
  state.selectedDecision = null;
}

function selectDecision(decision) {
  state.selectedDecision = decision;
  [el.decisionApproveBtn, el.decisionEditBtn, el.decisionRejectBtn].forEach((b) => b.classList.remove("is-active"));
  const map = { approved: el.decisionApproveBtn, edited: el.decisionEditBtn, rejected: el.decisionRejectBtn };
  map[decision].classList.add("is-active");
  el.correctedContentField.hidden = decision !== "edited";
}

async function submitReview() {
  if (!state.currentReview) return;
  const reviewerName = el.reviewerNameInput.value.trim();
  if (!reviewerName) {
    alert("Please enter your name for the audit log.");
    el.reviewerNameInput.focus();
    return;
  }
  if (!state.selectedDecision) {
    alert("Please choose a decision: Approve, Edit & approve, or Reject.");
    return;
  }

  try {
    await Api.submitReviewDecision({
      message_id: state.currentReview.message_id,
      reviewer_name: reviewerName,
      decision: state.selectedDecision,
      corrected_content: state.selectedDecision === "edited" ? el.correctedContentInput.value : null,
      notes: el.reviewNotesInput.value.trim() || null,
    });
    const reviewedConversationId = state.currentReview.conversation_id;
    closeReviewModal();
    refreshPendingReviews();
    if (reviewedConversationId === state.conversationId) {
      loadConversation(state.conversationId, el.conversationTitle.textContent);
    }
  } catch (e) {
    alert(`Failed to submit review: ${e.message}`);
  }
}

/* --------------------------------- icons --------------------------------- */

const ICONS = {
  user: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  assistant: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2-7 4 14 2-7h6"/></svg>`,
};
