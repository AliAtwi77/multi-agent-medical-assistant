// Thin HTTP client wrapping every backend endpoint.
// The UI layer (app.js) never calls fetch() directly — it goes through this module.

const Api = {
  async sendChatMessage({ conversationId, message, imageId }) {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, message, image_id: imageId || null }),
    });
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async uploadImage(file, prompt, conversationId) {
    const form = new FormData();
    form.append("file", file);
    form.append("prompt", prompt || "Analyze this medical image and describe any notable findings.");
    if (conversationId) form.append("conversation_id", conversationId);
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/imaging/upload`, { method: "POST", body: form });
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async listConversations() {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/conversations`);
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async getConversationMessages(conversationId) {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/conversations/${conversationId}/messages`);
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async listPendingReviews() {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/reviews/pending`);
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async submitReviewDecision(payload) {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/reviews/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async speechToText(audioBlob) {
    const form = new FormData();
    form.append("file", audioBlob, "recording.webm");
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/voice/speech-to-text`, { method: "POST", body: form });
    if (!res.ok) throw await Api._error(res);
    return res.json();
  },

  async textToSpeech(text) {
    const res = await fetch(`${API_CONFIG.BASE_URL}/api/voice/text-to-speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw await Api._error(res);
    return res.blob();
  },

  async _error(res) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {}
    return new Error(detail);
  },
};
