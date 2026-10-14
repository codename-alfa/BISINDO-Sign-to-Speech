import './style.css';
import { SpeechManager } from './modules/speechManager.js';
import { KeywordMatcher } from './modules/keywordMatcher.js';
import { MockPredictionEngine } from './modules/mockPredictionEngine.js';

class BisindoApp {
  constructor() {
    this.speechManager = new SpeechManager();
    this.keywordMatcher = new KeywordMatcher();
    this.predictionEngine = new MockPredictionEngine();

    this.currentMode = 'mode1'; // 'mode1' | 'mode2'
    this.cameraStream = null;
    this.isCameraActive = false;
    this.useFrontCamera = true;
    
    // Hand tracking variables
    this.mediaPipeHands = null;
    this.isTrackingRunning = false;
    this.lastDetectedGestureTime = 0;
    this.clearGestureTimeout = null;

    // DOM Elements
    this.dom = {
      // Navigation
      btnModeSign: document.getElementById('btn-mode-sign'),
      btnModeSpeech: document.getElementById('btn-mode-speech'),
      viewMode1: document.getElementById('view-mode1'),
      viewMode2: document.getElementById('view-mode2'),

      // Mode 1: Camera & Card
      cameraCard: document.getElementById('camera-card'),
      cameraFeed: document.getElementById('camera-feed'),
      cameraPrompt: document.getElementById('camera-prompt'),
      btnRequestCam: document.getElementById('btn-request-cam'),
      handBoundingBox: document.getElementById('hand-bounding-box'),
      translationCard: document.getElementById('translation-card'),
      cardMetaTitle: document.getElementById('card-meta-title'),
      confidencePill: document.getElementById('confidence-pill'),
      translatedWord: document.getElementById('translated-word'),
      audioWaveBars: document.getElementById('audio-wave-bars'),
      fallbackSuggestions: document.getElementById('fallback-suggestions'),
      fallbackChips: document.getElementById('fallback-chips'),

      // Mode 2: Speech
      speechCard: document.getElementById('speech-card'),
      btnToggleMic: document.getElementById('btn-toggle-mic'),
      speechHintText: document.getElementById('speech-hint-text'),
      speechStatusPill: document.getElementById('speech-status-pill'),
      speechTranscriptText: document.getElementById('speech-transcript-text'),
      speechVisualTags: document.getElementById('speech-visual-tags'),

      // Top Bar & Drawer
      btnCamToggle: document.getElementById('btn-cam-toggle'),
      btnDemoToggle: document.getElementById('btn-demo-panel-toggle'),
      demoDrawer: document.getElementById('demo-drawer'),
      btnCloseDrawer: document.getElementById('btn-close-drawer')
    };

    this.init();
  }

  init() {
    this.bindEvents();
    this.setupSpeechListeners();
    
    // 1. Initial State: Empty translation card before any detection
    this.clearHUD();

    // 2. Request and start camera for the middle screen space
    this.startCamera();
  }

  /* ==================== CAMERA MANAGEMENT (MIDDLE SCREEN) ==================== */
  async startCamera() {
    try {
      const constraints = {
        video: {
          facingMode: this.useFrontCamera ? 'user' : 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };

      if (this.cameraStream) {
        this.cameraStream.getTracks().forEach(t => t.stop());
      }

      this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
      this.dom.cameraFeed.srcObject = this.cameraStream;
      await this.dom.cameraFeed.play().catch(() => {});

      this.isCameraActive = true;
      if (this.dom.cameraPrompt) {
        this.dom.cameraPrompt.classList.add('hidden');
      }

      // Handle mirroring
      if (this.useFrontCamera) {
        this.dom.cameraFeed.classList.remove('unmirrored');
      } else {
        this.dom.cameraFeed.classList.add('unmirrored');
      }

      // Initialize real-time Hand Tracking
      this.initHandTracking();
    } catch (err) {
      console.warn('Camera permission pending or device unavailable:', err);
      if (this.dom.cameraPrompt) {
        this.dom.cameraPrompt.classList.remove('hidden');
      }
      this.isCameraActive = false;
    }
  }

  async flipCamera() {
    this.useFrontCamera = !this.useFrontCamera;
    await this.startCamera();
  }

  /* ==================== REAL-TIME HAND TRACKING ==================== */
  initHandTracking() {
    if (this.isTrackingRunning) return;

    // Check if Google MediaPipe Hands is loaded from CDN
    if (typeof window.Hands !== 'undefined') {
      try {
        this.mediaPipeHands = new window.Hands({
          locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
        });

        this.mediaPipeHands.setOptions({
          maxNumHands: 1,
          modelComplexity: 0, // Model complexity 0 for high speed / real-time tracking
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        this.mediaPipeHands.onResults((results) => {
          this.handleMediaPipeResults(results);
        });

        this.isTrackingRunning = true;
        this.runMediaPipeLoop();
        return;
      } catch (err) {
        console.warn('MediaPipe Hands setup error, falling back to CV tracker:', err);
      }
    }

    // Fallback: Lightweight optical skin/motion hand tracker
    this.startFallbackHandTracker();
  }

  async runMediaPipeLoop() {
    const process = async () => {
      if (this.isCameraActive && this.dom.cameraFeed && this.dom.cameraFeed.readyState >= 2) {
        try {
          await this.mediaPipeHands.send({ image: this.dom.cameraFeed });
        } catch (e) {
          // ignore transient frame processing error
        }
      }
      if (this.isCameraActive) {
        requestAnimationFrame(process);
      } else {
        this.isTrackingRunning = false;
      }
    };

    process();
  }

  handleMediaPipeResults(results) {
    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
      const landmarks = results.multiHandLandmarks[0];

      // Calculate Bounding Box
      let minX = 1, minY = 1, maxX = 0, maxY = 0;
      landmarks.forEach(pt => {
        if (pt.x < minX) minX = pt.x;
        if (pt.y < minY) minY = pt.y;
        if (pt.x > maxX) maxX = pt.x;
        if (pt.y > maxY) maxY = pt.y;
      });

      // Padding around hand
      const padX = (maxX - minX) * 0.18;
      const padY = (maxY - minY) * 0.18;
      minX = Math.max(0, minX - padX);
      minY = Math.max(0, minY - padY);
      maxX = Math.min(1, maxX + padX);
      maxY = Math.min(1, maxY + padY);

      // Coordinate mapping (mirroring if front camera)
      const leftPercent = this.useFrontCamera ? (1 - maxX) * 100 : minX * 100;
      const topPercent = minY * 100;
      const widthPercent = (maxX - minX) * 100;
      const heightPercent = (maxY - minY) * 100;

      // Update Bounding Box position in real-time
      this.dom.handBoundingBox.style.left = `${leftPercent}%`;
      this.dom.handBoundingBox.style.top = `${topPercent}%`;
      this.dom.handBoundingBox.style.width = `${widthPercent}%`;
      this.dom.handBoundingBox.style.height = `${heightPercent}%`;
      this.dom.handBoundingBox.classList.add('visible');

      // Simple heuristic gesture recognition:
      // Raised open hand: fingertips extended above wrist and knuckle joints
      const isRaisedOpenPalm = (
        landmarks[8].y < landmarks[6].y &&
        landmarks[12].y < landmarks[10].y &&
        landmarks[16].y < landmarks[14].y &&
        landmarks[20].y < landmarks[18].y
      );

      const now = Date.now();
      if (isRaisedOpenPalm && now - this.lastDetectedGestureTime > 5000) {
        this.triggerDetection('TERIMA KASIH', '96%');
      }
    } else {
      // Hide bounding box when no hand is in view
      this.dom.handBoundingBox.classList.remove('visible');
    }
  }

  /* Fallback CV Hand Tracker (Skin color / Motion cluster tracker) */
  startFallbackHandTracker() {
    const canvas = document.createElement('canvas');
    canvas.width = 160;
    canvas.height = 120;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    let smoothedX = 50;
    let smoothedY = 50;
    let smoothedW = 40;
    let smoothedH = 40;

    const track = () => {
      if (this.isCameraActive && this.dom.cameraFeed && this.dom.cameraFeed.readyState >= 2) {
        ctx.drawImage(this.dom.cameraFeed, 0, 0, canvas.width, canvas.height);
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imgData.data;

        let totalX = 0, totalY = 0, count = 0;
        let minX = canvas.width, minY = canvas.height, maxX = 0, maxY = 0;

        // Sample skin tone pixel coordinates
        for (let y = 10; y < canvas.height - 10; y += 4) {
          for (let x = 10; x < canvas.width - 10; x += 4) {
            const idx = (y * canvas.width + x) * 4;
            const r = data[idx], g = data[idx + 1], b = data[idx + 2];

            // Simplified skin tone detection
            if (r > 95 && g > 40 && b > 20 && r > g && r > b && Math.abs(r - g) > 15) {
              totalX += x;
              totalY += y;
              count++;
              if (x < minX) minX = x;
              if (x > maxX) maxX = x;
              if (y < minY) minY = y;
              if (y > maxY) maxY = y;
            }
          }
        }

        if (count > 35) {
          let targetX = (minX / canvas.width) * 100;
          let targetY = (minY / canvas.height) * 100;
          let targetW = ((maxX - minX) / canvas.width) * 100;
          let targetH = ((maxY - minY) / canvas.height) * 100;

          if (this.useFrontCamera) {
            targetX = 100 - (targetX + targetW);
          }

          // Smooth interpolation
          smoothedX += (targetX - smoothedX) * 0.25;
          smoothedY += (targetY - smoothedY) * 0.25;
          smoothedW += (Math.max(25, targetW) - smoothedW) * 0.25;
          smoothedH += (Math.max(25, targetH) - smoothedH) * 0.25;

          this.dom.handBoundingBox.style.left = `${smoothedX}%`;
          this.dom.handBoundingBox.style.top = `${smoothedY}%`;
          this.dom.handBoundingBox.style.width = `${smoothedW}%`;
          this.dom.handBoundingBox.style.height = `${smoothedH}%`;
          this.dom.handBoundingBox.classList.add('visible');
        } else {
          this.dom.handBoundingBox.classList.remove('visible');
        }
      }

      if (this.isCameraActive) {
        requestAnimationFrame(track);
      }
    };

    track();
  }

  /* ==================== TRANSLATION OUTPUT HUD & EMPTY STATE ==================== */
  clearHUD() {
    this.dom.translatedWord.textContent = '';
    this.dom.translatedWord.classList.add('empty');
    this.dom.confidencePill.textContent = '';
    this.dom.confidencePill.classList.add('hidden');
    this.dom.fallbackSuggestions.classList.add('hidden');
    this.dom.audioWaveBars.classList.add('hidden');
  }

  triggerDetection(word, confidence = '96%', isConfident = true) {
    this.lastDetectedGestureTime = Date.now();
    this.updateHUD(word, confidence, isConfident);
    this.speakWord(word);

    // Auto-clear back to empty after 4.5 seconds if no new detection occurs
    clearTimeout(this.clearGestureTimeout);
    this.clearGestureTimeout = setTimeout(() => {
      this.clearHUD();
    }, 4500);
  }

  updateHUD(word, confidence = '96%', isConfident = true) {
    this.dom.translatedWord.textContent = word;
    this.dom.translatedWord.classList.remove('empty');
    this.dom.confidencePill.textContent = confidence;
    this.dom.confidencePill.classList.remove('hidden');

    if (isConfident) {
      this.dom.confidencePill.className = 'confidence-pill';
      this.dom.fallbackSuggestions.classList.add('hidden');
    } else {
      this.dom.confidencePill.className = 'confidence-pill low';
      this.renderFallbackChips(['Tolong', 'Halo', 'Terima kasih']);
      this.dom.fallbackSuggestions.classList.remove('hidden');
    }
  }

  renderFallbackChips(suggestions) {
    this.dom.fallbackChips.innerHTML = '';
    suggestions.forEach(w => {
      const chip = document.createElement('button');
      chip.className = 'fallback-chip-btn';
      chip.textContent = w;
      chip.addEventListener('click', (e) => {
        e.stopPropagation();
        this.triggerDetection(w.toUpperCase(), '92%', true);
      });
      this.dom.fallbackChips.appendChild(chip);
    });
  }

  speakWord(text) {
    this.dom.audioWaveBars.classList.remove('hidden');
    this.speechManager.speak(
      text,
      true,
      () => this.dom.audioWaveBars.classList.remove('hidden'),
      () => this.dom.audioWaveBars.classList.add('hidden')
    );
  }

  /* ==================== EVENT BINDINGS ==================== */
  bindEvents() {
    // Mode Switcher (Segmented Nav)
    this.dom.btnModeSign.addEventListener('click', () => this.switchMode('mode1'));
    this.dom.btnModeSpeech.addEventListener('click', () => this.switchMode('mode2'));

    // Camera Activation & Flip Buttons
    if (this.dom.btnRequestCam) {
      this.dom.btnRequestCam.addEventListener('click', (e) => {
        e.stopPropagation();
        this.startCamera();
      });
    }

    if (this.dom.cameraCard) {
      this.dom.cameraCard.addEventListener('click', () => {
        if (!this.isCameraActive) {
          this.startCamera();
        }
      });
    }

    this.dom.btnCamToggle.addEventListener('click', () => this.flipCamera());

    // Click Translation Card to Speak (TTS)
    this.dom.translationCard.addEventListener('click', () => {
      const word = this.dom.translatedWord.textContent.trim();
      if (word && word !== 'TIDAK YAKIN') {
        this.speakWord(word);
      }
    });

    // Mode 2: Mic Toggle
    this.dom.btnToggleMic.addEventListener('click', () => this.handleMicToggle());

    // Mode 2: Quick Speech Samples
    document.querySelectorAll('.speech-sample-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const text = btn.dataset.sample;
        this.processSpokenText(text);
      });
    });

    // Presenter Drawer Toggle
    this.dom.btnDemoToggle.addEventListener('click', () => this.toggleDrawer());
    this.dom.btnCloseDrawer.addEventListener('click', () => this.toggleDrawer(false));

    // Demo Drawer Word Buttons
    document.querySelectorAll('.demo-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        if (action === 'sim-word') {
          const word = btn.dataset.word;
          const conf = btn.dataset.conf || '95%';
          this.switchMode('mode1');
          this.triggerDetection(word.toUpperCase(), conf, true);
        } else if (action === 'sim-uncertain') {
          this.switchMode('mode1');
          this.triggerDetection('TIDAK YAKIN', '54%', false);
        }
      });
    });

    // Global Keyboard Shortcuts (Presenter Mode)
    window.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
  }

  /* ==================== SPEECH RECOGNITION (STT) SETUP ==================== */
  setupSpeechListeners() {
    this.speechManager.onSTTStart = () => {
      this.dom.btnToggleMic.classList.add('active');
      document.querySelector('.speech-mic-area').classList.add('recording');
      this.dom.speechHintText.textContent = 'Mendengarkan... Silakan berbicara.';
    };

    this.speechManager.onSTTResult = ({ final, interim }) => {
      const activeText = final || interim;
      if (activeText) {
        this.processSpokenText(activeText);
      }
    };

    this.speechManager.onSTTEnd = () => {
      this.dom.btnToggleMic.classList.remove('active');
      document.querySelector('.speech-mic-area').classList.remove('recording');
      this.dom.speechHintText.textContent = 'Tekan tombol mikrofon untuk berbicara...';
    };

    this.speechManager.onSTTError = (error) => {
      console.warn('STT Error:', error);
      this.dom.speechHintText.textContent = 'Izin mikrofon diperlukan atau gunakan contoh suara cepat.';
    };
  }

  /* ==================== MODE SWITCHING ==================== */
  switchMode(mode) {
    this.currentMode = mode;

    if (mode === 'mode1') {
      this.dom.btnModeSign.classList.add('active');
      this.dom.btnModeSpeech.classList.remove('active');
      this.dom.viewMode1.classList.add('active');
      this.dom.viewMode2.classList.remove('active');
      this.speechManager.stopListening();
      if (!this.isCameraActive) {
        this.startCamera();
      }
    } else {
      this.dom.btnModeSpeech.classList.add('active');
      this.dom.btnModeSign.classList.remove('active');
      this.dom.viewMode2.classList.add('active');
      this.dom.viewMode1.classList.remove('active');
      this.speechManager.stopSpeech();
    }
  }

  /* ==================== MODE 2 LOGIC ==================== */
  handleMicToggle() {
    const status = this.speechManager.toggleListening();
    if (!status.supported) {
      this.processSpokenText('Silakan bayar obat di kasir');
    }
  }

  processSpokenText(text) {
    this.dom.speechTranscriptText.textContent = `"${text.toUpperCase()}"`;
    this.dom.speechStatusPill.textContent = '100%';
    this.dom.speechStatusPill.classList.remove('hidden');
    const matches = this.keywordMatcher.match(text);
    this.renderVisualPills(matches);
  }

  renderVisualPills(matches) {
    this.dom.speechVisualTags.innerHTML = '';
    this.dom.speechVisualTags.classList.remove('hidden');

    if (matches.length === 0) {
      this.dom.speechVisualTags.innerHTML = `
        <div class="visual-pill-item"><span class="pill-emoji">💬</span><span class="pill-label">SUARA DITERIMA</span></div>
      `;
      return;
    }

    matches.forEach(item => {
      const pill = document.createElement('div');
      pill.className = 'visual-pill-item';
      pill.innerHTML = `
        <span class="pill-emoji">${item.iconEmoji}</span>
        <span class="pill-label">${item.title.toUpperCase()}</span>
      `;
      this.dom.speechVisualTags.appendChild(pill);
    });
  }

  /* ==================== PRESENTER DRAWER & HOTKEYS ==================== */
  toggleDrawer(forceState = null) {
    if (forceState !== null) {
      this.dom.demoDrawer.classList.toggle('hidden', !forceState);
    } else {
      this.dom.demoDrawer.classList.toggle('hidden');
    }
  }

  handleKeyboardShortcuts(e) {
    const key = e.key.toLowerCase();

    // Reset / Clear card (Escape or C)
    if (key === 'escape' || key === 'c') {
      this.clearHUD();
      return;
    }

    // Toggle drawer
    if (key === 'd') {
      this.toggleDrawer();
      return;
    }

    // Toggle Mode
    if (key === 'm') {
      this.switchMode(this.currentMode === 'mode1' ? 'mode2' : 'mode1');
      return;
    }

    // Word Shortcuts
    const shortcuts = {
      '1': { word: 'TERIMA KASIH', conf: '96%' },
      '2': { word: 'HALO', conf: '94%' },
      '3': { word: 'TOLONG', conf: '91%' },
      '4': { word: 'YA', conf: '95%' },
      '5': { word: 'TIDAK', conf: '92%' }
    };

    if (shortcuts[key]) {
      this.switchMode('mode1');
      const item = shortcuts[key];
      this.triggerDetection(item.word, item.conf, true);
      return;
    }

    // Low confidence simulation
    if (key === '0') {
      this.switchMode('mode1');
      this.triggerDetection('TIDAK YAKIN', '54%', false);
      return;
    }

    // Spacebar trigger
    if (key === ' ' || e.code === 'Space') {
      e.preventDefault();
      if (this.currentMode === 'mode1') {
        const word = this.dom.translatedWord.textContent.trim();
        if (word && word !== 'TIDAK YAKIN') {
          this.speakWord(word);
        } else {
          this.triggerDetection('TERIMA KASIH', '96%', true);
        }
      } else {
        this.handleMicToggle();
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new BisindoApp();
});
