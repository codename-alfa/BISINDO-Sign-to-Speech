/**
 * SpeechManager - Bi-Directional Speech Handling
 * - Text-To-Speech (TTS): Web Speech Synthesis API (Locale id-ID)
 * - Speech-To-Text (STT): Web Speech Recognition API (Locale id-ID)
 */

export class SpeechManager {
  constructor() {
    this.synth = window.speechSynthesis || null;
    this.voices = [];
    this.idVoice = null;
    this.lastSpokenText = '';
    this.lastSpokenTime = 0;
    this.isSpeaking = false;

    // STT variables
    this.recognition = null;
    this.isListening = false;
    this.onSTTResult = null;
    this.onSTTError = null;
    this.onSTTEnd = null;
    this.onSTTStart = null;

    this.initTTS();
    this.initSTT();
  }

  /* ==================== TEXT TO SPEECH (TTS) ==================== */
  initTTS() {
    if (!this.synth) {
      console.warn('Web Speech Synthesis API not supported in this browser.');
      return;
    }

    const loadVoices = () => {
      this.voices = this.synth.getVoices();
      // Try to find Indonesian voice
      this.idVoice = this.voices.find(v => v.lang === 'id-ID' || v.lang === 'id' || v.lang === 'in-ID') || null;
    };

    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  speak(text, force = false, onStartCb = null, onEndCb = null) {
    if (!this.synth || !text.trim()) return false;

    const now = Date.now();
    // Debounce 1.2s to prevent repetitive spam unless forced
    if (!force && text === this.lastSpokenText && now - this.lastSpokenTime < 1200) {
      return false;
    }

    this.synth.cancel(); // Stop any pending speech

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'id-ID';
    if (this.idVoice) {
      utterance.voice = this.idVoice;
    }
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      this.isSpeaking = true;
      if (onStartCb) onStartCb();
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      if (onEndCb) onEndCb();
    };

    utterance.onerror = (e) => {
      console.error('TTS Error:', e);
      this.isSpeaking = false;
      if (onEndCb) onEndCb();
    };

    this.synth.speak(utterance);
    this.lastSpokenText = text;
    this.lastSpokenTime = now;
    return true;
  }

  stopSpeech() {
    if (this.synth) {
      this.synth.cancel();
      this.isSpeaking = false;
    }
  }

  /* ==================== SPEECH TO TEXT (STT) ==================== */
  initSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not available in this browser. Fallback input will be used.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.lang = 'id-ID';
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      this.isListening = true;
      if (this.onSTTStart) this.onSTTStart();
    };

    this.recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (this.onSTTResult) {
        this.onSTTResult({
          final: finalTranscript.trim(),
          interim: interimTranscript.trim()
        });
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('STT Error event:', event.error);
      if (this.onSTTError) {
        this.onSTTError(event.error);
      }
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (this.onSTTEnd) this.onSTTEnd();
    };
  }

  toggleListening() {
    if (!this.recognition) {
      return { supported: false, isListening: false };
    }

    if (this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    } else {
      try {
        this.recognition.start();
        this.isListening = true;
      } catch (err) {
        console.error('Error starting recognition:', err);
      }
    }

    return { supported: true, isListening: this.isListening };
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }
}
