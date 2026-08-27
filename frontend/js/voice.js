// Wraps the browser MediaRecorder API to capture microphone audio as a Blob,
// which app.js then sends to the backend /api/voice/speech-to-text endpoint.

const VoiceRecorder = {
  _mediaRecorder: null,
  _chunks: [],
  _stream: null,

  async start() {
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this._chunks = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    this._mediaRecorder = new MediaRecorder(this._stream, mimeType ? { mimeType } : undefined);
    this._mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) this._chunks.push(e.data);
    };
    this._mediaRecorder.start();
  },

  stop() {
    return new Promise((resolve, reject) => {
      if (!this._mediaRecorder) return reject(new Error("Recorder was not started."));
      this._mediaRecorder.onstop = () => {
        const blob = new Blob(this._chunks, { type: this._mediaRecorder.mimeType || "audio/webm" });
        this._stream.getTracks().forEach((t) => t.stop());
        resolve(blob);
      };
      this._mediaRecorder.stop();
    });
  },

  isSupported() {
    return !!(navigator.mediaDevices && window.MediaRecorder);
  },
};
