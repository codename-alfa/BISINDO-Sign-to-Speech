/**
 * MockPredictionEngine - Edge ML Inference Simulator
 * Implements the heuristic prediction engine specified in docs/one_week_mockup_plan.md.
 * Manages confidence thresholds (>=70% vs <70%), suggestions fallback, and latency SLA.
 */

export const MVP_WORDS = [
  { word: 'Terima kasih', type: 'Dinamis', description: 'Gerakan tangan menyatu di dada/dagu menuju lawan bicara' },
  { word: 'Halo', type: 'Dinamis', description: 'Lambaian telapak tangan terbuka setinggi bahu' },
  { word: 'Tolong', type: 'Dinamis', description: 'Tangan menopang telapak tangan lain memohon bantuan' },
  { word: 'Ya', type: 'Statis/Dinamis', description: 'Gerakan anggukan kepalan tangan setuju' },
  { word: 'Tidak', type: 'Dinamis', description: 'Gerakan gelengan telunjuk ke kiri dan kanan' }
];

export class MockPredictionEngine {
  constructor() {
    this.currentWord = 'Terima kasih';
    this.currentConfidence = 0.94;
    this.topSuggestions = [];
    this.isUncertain = false;
    this.latency = 38; // ms
  }

  /**
   * Simulate a confident detection (Confidence >= 70%)
   * @param {string} word 
   * @param {number|null} targetConfidence 
   */
  simulateConfidentSign(word = 'Terima kasih', targetConfidence = null) {
    this.currentWord = word;
    this.currentConfidence = targetConfidence || (0.86 + Math.random() * 0.10);
    this.currentConfidence = Math.min(0.98, parseFloat(this.currentConfidence.toFixed(2)));
    this.topSuggestions = [];
    this.isUncertain = false;
    this.latency = Math.floor(34 + Math.random() * 18); // 34ms - 52ms (well under 100ms SLA)

    return {
      word: this.currentWord,
      confidence: this.currentConfidence,
      confidencePercent: Math.round(this.currentConfidence * 100),
      isHighConfidence: true,
      suggestions: [],
      latency: this.latency,
      subtext: `Isyarat dinamis "${this.currentWord}" terdeteksi stabil oleh Edge AI`
    };
  }

  /**
   * Simulate an uncertain detection (Confidence < 70%) to demonstrate fallback logic
   */
  simulateUncertainSign() {
    this.currentWord = 'Tidak Yakin';
    this.currentConfidence = 0.54;
    this.isUncertain = true;
    this.topSuggestions = ['Tolong', 'Halo', 'Terima kasih'];
    this.latency = Math.floor(40 + Math.random() * 12);

    return {
      word: this.currentWord,
      confidence: this.currentConfidence,
      confidencePercent: Math.round(this.currentConfidence * 100),
      isHighConfidence: false,
      suggestions: this.topSuggestions,
      latency: this.latency,
      subtext: 'Tingkat keyakinan < 70%. Silakan pilih salah satu kata alternatif di bawah:'
    };
  }

  /**
   * Draw simulated 21 3D MediaPipe hand keypoints on the canvas overlay
   * @param {CanvasRenderingContext2D} ctx 
   * @param {number} width 
   * @param {number} height 
   * @param {number} timestamp 
   */
  drawSimulatedHandLandmarks(ctx, width, height, timestamp) {
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    // Subtle breathing animation based on timestamp
    const t = timestamp * 0.003;
    const offsetX = Math.sin(t) * 12;
    const offsetY = Math.cos(t * 0.8) * 8;

    const centerX = width * 0.5 + offsetX;
    const centerY = height * 0.52 + offsetY;
    const scale = Math.min(width, height) * 0.38;

    // 21 Canonical MediaPipe Hand Landmarks relative coordinates (-1 to 1)
    const normalizedPoints = [
      // Wrist (0)
      [0.0, 0.45],
      // Thumb (1, 2, 3, 4)
      [-0.15, 0.35], [-0.28, 0.22], [-0.35, 0.08], [-0.40, -0.05],
      // Index (5, 6, 7, 8)
      [-0.12, 0.05], [-0.15, -0.15], [-0.16, -0.32], [-0.17, -0.45],
      // Middle (9, 10, 11, 12)
      [0.0, 0.0], [0.0, -0.22], [0.0, -0.38], [0.0, -0.52],
      // Ring (13, 14, 15, 16)
      [0.12, 0.05], [0.15, -0.18], [0.16, -0.33], [0.17, -0.46],
      // Pinky (17, 18, 19, 20)
      [0.24, 0.12], [0.28, -0.05], [0.30, -0.18], [0.32, -0.30]
    ];

    const screenPoints = normalizedPoints.map(([nx, ny]) => [
      centerX + nx * scale,
      centerY + ny * scale
    ]);

    // Hand Skeleton Connections (MediaPipe Hand Connections)
    const connections = [
      // Palm base
      [0, 1], [1, 2], [2, 3], [3, 4],
      [0, 5], [5, 6], [6, 7], [7, 8],
      [5, 9], [9, 10], [10, 11], [11, 12],
      [9, 13], [13, 14], [14, 15], [15, 16],
      [13, 17], [17, 18], [18, 19], [19, 20],
      [0, 17]
    ];

    // Glow effect
    ctx.save();
    ctx.shadowBlur = 10;
    ctx.shadowColor = this.isUncertain ? 'rgba(245, 158, 11, 0.8)' : 'rgba(16, 185, 129, 0.8)';

    // Draw bones / connections
    ctx.strokeStyle = this.isUncertain ? 'rgba(245, 158, 11, 0.65)' : 'rgba(16, 185, 129, 0.7)';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    for (const [p1, p2] of connections) {
      const [x1, y1] = screenPoints[p1];
      const [x2, y2] = screenPoints[p2];
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Draw joints / nodes
    for (let i = 0; i < screenPoints.length; i++) {
      const [px, py] = screenPoints[i];
      const isTip = [4, 8, 12, 16, 20].includes(i);

      ctx.beginPath();
      ctx.arc(px, py, isTip ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = isTip ? '#FFFFFF' : (this.isUncertain ? '#F59E0B' : '#10B981');
      ctx.fill();

      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.restore();
  }
}
