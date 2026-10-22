import { requestApi } from "@/core/api";
import type { AppLocale } from "@/i18n";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error" | "permission_denied";

export interface VoiceTranscriptUpdate {
  partialTranscript: string;
  finalTranscript: string;
}

export interface VoiceServiceCallbacks {
  onStateChange?: (state: VoiceState) => void;
  onTranscriptUpdate?: (payload: VoiceTranscriptUpdate) => void;
  onError?: (message: string) => void;
  onVolume?: (normalizedDb: number) => void;
}

interface TranscribeResponse {
  text?: string;
  partial?: string;
  final?: string;
}

interface SpeechResponse {
  audio_url?: string;
  audio_base64?: string;
  mime_type?: string;
}

function getMimeType(): string {
  const preferred = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const type of preferred) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "";
}

function createAudioBlob(chunks: BlobPart[], mimeType: string): Blob {
  return new Blob(chunks, { type: mimeType || "audio/webm" });
}

function decodeAudioBase64(input: string): ArrayBuffer {
  const binary = atob(input);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}

function normalizeVolumeToDecibel(normalized: number): number {
  const safe = Math.min(Math.max(normalized, 0.0001), 1);
  return 20 * Math.log10(safe);
}

export class VoiceService {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private rafId: number | null = null;
  private chunks: BlobPart[] = [];
  private partialTranscript = "";
  private finalTranscript = "";
  private readonly callbacks: VoiceServiceCallbacks;
  private ttsAudio: HTMLAudioElement | null = null;
  private ttsEnabled = true;
  private locale: AppLocale = "en";
  private isPlayingTts = false;
  private isLiveTranscribing = false;
  private pendingLiveChunk: Blob | null = null;

  constructor(callbacks: VoiceServiceCallbacks = {}) {
    this.callbacks = callbacks;
  }

  setLocale(locale: AppLocale): void {
    this.locale = locale;
  }

  setTtsEnabled(value: boolean): void {
    this.ttsEnabled = value;
  }

  getTranscript(): VoiceTranscriptUpdate {
    return {
      partialTranscript: this.partialTranscript,
      finalTranscript: this.finalTranscript
    };
  }

  async startListening(): Promise<void> {
    this.stopTts();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
    } catch {
      this.callbacks.onStateChange?.("permission_denied");
      this.callbacks.onError?.("microphone_permission_denied");
      return;
    }

    this.setupVolumeAnalyzer(this.stream);

    const mimeType = getMimeType();
    this.mediaRecorder = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
    this.chunks = [];
    this.partialTranscript = "";
    this.callbacks.onTranscriptUpdate?.(this.getTranscript());

    this.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data);
        void this.enqueueLiveTranscription(event.data, mimeType);
      }
    });

    this.mediaRecorder.addEventListener("stop", () => {
      void this.flushTranscription(mimeType);
    });

    this.mediaRecorder.start(1000);
    this.callbacks.onStateChange?.("listening");
  }

  stopListening(): void {
    if (!this.mediaRecorder) return;
    if (this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    this.cleanupStream();
  }

  async speak(text: string): Promise<void> {
    if (!this.ttsEnabled) return;
    if (!text.trim()) return;
    this.stopTts();
    this.callbacks.onStateChange?.("speaking");
    this.isPlayingTts = true;

    try {
      const speech = await requestApi<SpeechResponse, { text: string; language: string }>({
        method: "POST",
        url: "/v1/audio/speech",
        data: {
          text,
          language: this.locale
        }
      });

      if (speech.audio_url) {
        const audio = new Audio(speech.audio_url);
        this.ttsAudio = audio;
        audio.addEventListener("ended", () => {
          this.isPlayingTts = false;
          this.callbacks.onStateChange?.("idle");
        });
        audio.addEventListener("error", () => {
          this.isPlayingTts = false;
          this.callbacks.onStateChange?.("error");
          this.callbacks.onError?.("tts_failed");
        });
        await audio.play();
        return;
      }

      if (speech.audio_base64) {
        const buffer = decodeAudioBase64(speech.audio_base64);
        const blob = new Blob([buffer], { type: speech.mime_type || "audio/mpeg" });
        const objectUrl = URL.createObjectURL(blob);
        const audio = new Audio(objectUrl);
        this.ttsAudio = audio;
        audio.addEventListener("ended", () => {
          this.isPlayingTts = false;
          URL.revokeObjectURL(objectUrl);
          this.callbacks.onStateChange?.("idle");
        });
        audio.addEventListener("error", () => {
          this.isPlayingTts = false;
          URL.revokeObjectURL(objectUrl);
          this.callbacks.onStateChange?.("error");
          this.callbacks.onError?.("tts_failed");
        });
        await audio.play();
        return;
      }

      this.isPlayingTts = false;
      this.callbacks.onStateChange?.("idle");
    } catch {
      this.isPlayingTts = false;
      this.callbacks.onStateChange?.("error");
      this.callbacks.onError?.("tts_failed");
    }
  }

  stopTts(): void {
    if (this.ttsAudio) {
      this.ttsAudio.pause();
      this.ttsAudio.currentTime = 0;
      this.ttsAudio = null;
    }
    this.isPlayingTts = false;
  }

  reset(): void {
    this.stopListening();
    this.stopTts();
    this.partialTranscript = "";
    this.finalTranscript = "";
    this.callbacks.onTranscriptUpdate?.(this.getTranscript());
    this.callbacks.onStateChange?.("idle");
  }

  private async flushTranscription(mimeType: string): Promise<void> {
    if (this.chunks.length === 0) {
      this.callbacks.onStateChange?.("idle");
      return;
    }

    this.callbacks.onStateChange?.("processing");

    const audioBlob = createAudioBlob(this.chunks, mimeType);
    this.chunks = [];

    const formData = new FormData();
    formData.set("file", audioBlob, "voice-input.webm");
    formData.set("language", this.locale);

    try {
      const response = await requestApi<TranscribeResponse, FormData>({
        method: "POST",
        url: "/v1/audio/transcribe",
        data: formData,
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      const partial = (response.partial ?? "").trim();
      const finalChunk = (response.final ?? response.text ?? "").trim();
      this.partialTranscript = partial;
      if (finalChunk) {
        this.finalTranscript = this.finalTranscript
          ? `${this.finalTranscript} ${finalChunk}`.trim()
          : finalChunk;
      }
      this.callbacks.onTranscriptUpdate?.(this.getTranscript());
      this.callbacks.onStateChange?.("idle");
    } catch {
      this.callbacks.onStateChange?.("error");
      this.callbacks.onError?.("stt_failed");
    }
  }

  private async enqueueLiveTranscription(chunk: Blob, mimeType: string): Promise<void> {
    if (this.mediaRecorder?.state !== "recording") {
      return;
    }

    if (this.isLiveTranscribing) {
      this.pendingLiveChunk = chunk;
      return;
    }

    this.isLiveTranscribing = true;
    try {
      await this.transcribeLiveChunk(chunk, mimeType);
      while (this.pendingLiveChunk) {
        const nextChunk = this.pendingLiveChunk;
        this.pendingLiveChunk = null;
        await this.transcribeLiveChunk(nextChunk, mimeType);
      }
    } finally {
      this.isLiveTranscribing = false;
    }
  }

  private async transcribeLiveChunk(chunk: Blob, mimeType: string): Promise<void> {
    if (chunk.size === 0) {
      return;
    }

    const formData = new FormData();
    const liveBlob = new Blob([chunk], { type: mimeType || "audio/webm" });
    formData.set("file", liveBlob, "voice-live.webm");
    formData.set("language", this.locale);

    try {
      const response = await requestApi<TranscribeResponse, FormData>({
        method: "POST",
        url: "/v1/audio/transcribe",
        data: formData,
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      const liveText = (response.partial ?? response.text ?? "").trim();
      if (!liveText) {
        return;
      }
      this.partialTranscript = liveText;
      this.callbacks.onTranscriptUpdate?.(this.getTranscript());
    } catch {
      // Ignore transient live-chunk failures and preserve final transcription behavior.
    }
  }

  private setupVolumeAnalyzer(stream: MediaStream): void {
    this.audioContext = new AudioContext();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 1024;
    this.sourceNode = this.audioContext.createMediaStreamSource(stream);
    this.sourceNode.connect(this.analyser);

    const buffer = new Uint8Array(this.analyser.frequencyBinCount);

    const tick = () => {
      if (!this.analyser) return;
      this.analyser.getByteFrequencyData(buffer);
      const sum = buffer.reduce((accumulator, value) => accumulator + value, 0);
      const avg = sum / Math.max(buffer.length, 1);
      const normalized = Math.min(Math.max(avg / 255, 0), 1);
      const db = normalizeVolumeToDecibel(normalized);
      this.callbacks.onVolume?.(normalized);

      if (this.isPlayingTts && db > -26) {
        this.stopTts();
      }

      this.rafId = window.requestAnimationFrame(tick);
    };

    tick();
  }

  private cleanupStream(): void {
    this.pendingLiveChunk = null;
    this.isLiveTranscribing = false;
    if (this.rafId !== null) {
      window.cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }

    if (this.audioContext) {
      void this.audioContext.close();
      this.audioContext = null;
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => {
        track.stop();
      });
      this.stream = null;
    }
  }
}
