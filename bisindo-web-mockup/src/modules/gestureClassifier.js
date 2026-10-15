/**
 * GestureClassifier — Landmark-based hand gesture recognizer
 *
 * Supports three BISINDO gestures using MediaPipe 21-point hand landmarks:
 *   1. HALO         — Open palm facing the camera (all fingers extended toward viewer)
 *   2. TERIMA KASIH — Back of palm facing camera (fingers extended, dorsal side visible)
 *   3. CINTA        — "Metal / ILY" hand shape (index + pinky up, middle + ring folded)
 *
 * Emits "Tidak Terdeteksi" when no gesture matches with sufficient confidence.
 */

const MATCH_THRESHOLD = 0.42;
const HIGH_CONFIDENCE_THRESHOLD = 0.72;

function isExtended(lm, tip, pip, margin = 0.02) {
  return lm[tip].y < lm[pip].y - margin;
}

function isCurled(lm, tip, mcp, margin = 0.02) {
  return lm[tip].y > lm[mcp].y - margin;
}

function estimateOrientation(lm, isMirrored = true) {
  const thumbX = lm[2].x;
  const pinkyX = lm[17].x;
  const thumbIsLeft = thumbX < pinkyX;
  if (isMirrored) {
    return thumbIsLeft ? 'back' : 'palm';
  } else {
    return thumbIsLeft ? 'palm' : 'back';
  }
}

function scoreHalo(lm, isMirrored) {
  let score = 0;
  const indexUp  = isExtended(lm, 8,  6,  0.03);
  const middleUp = isExtended(lm, 12, 10, 0.03);
  const ringUp   = isExtended(lm, 16, 14, 0.03);
  const pinkyUp  = isExtended(lm, 20, 18, 0.02);
  const extendedCount = [indexUp, middleUp, ringUp, pinkyUp].filter(Boolean).length;
  score += (extendedCount / 4) * 0.55;
  const thumbExtended = Math.abs(lm[4].x - lm[5].x) > 0.06;
  if (thumbExtended) score += 0.1;
  const orientation = estimateOrientation(lm, isMirrored);
  if (orientation === 'palm') score += 0.25;
  else if (orientation === 'unknown') score += 0.05;
  const spread = Math.abs(lm[8].x - lm[20].x);
  score += Math.min(1, spread / 0.15) * 0.1;
  return Math.min(1.0, score);
}

function scoreTerimakasih(lm, isMirrored) {
  let score = 0;
  const indexUp  = isExtended(lm, 8,  6,  0.03);
  const middleUp = isExtended(lm, 12, 10, 0.03);
  const ringUp   = isExtended(lm, 16, 14, 0.03);
  const pinkyUp  = isExtended(lm, 20, 18, 0.02);
  const extendedCount = [indexUp, middleUp, ringUp, pinkyUp].filter(Boolean).length;
  score += (extendedCount / 4) * 0.50;
  const orientation = estimateOrientation(lm, isMirrored);
  if (orientation === 'back') score += 0.35;
  else if (orientation === 'unknown') score += 0.08;
  const spread = Math.abs(lm[8].x - lm[20].x);
  if (spread < 0.18) score += 0.1;
  else score += Math.max(0, (0.25 - spread) / 0.25) * 0.1;
  const thumbSpread = Math.abs(lm[4].x - lm[5].x);
  if (thumbSpread < 0.12) score += 0.05;
  return Math.min(1.0, score);
}

function scoreCinta(lm, isMirrored) {
  let score = 0;
  const indexUp    = isExtended(lm, 8,  6,  0.04);
  const pinkyUp    = isExtended(lm, 20, 18, 0.04);
  const middleDown = isCurled(lm, 12, 9,  0.02);
  const ringDown   = isCurled(lm, 16, 13, 0.02);
  if (indexUp)    score += 0.25;
  if (pinkyUp)    score += 0.25;
  if (middleDown) score += 0.22;
  if (ringDown)   score += 0.18;
  const spread = Math.abs(lm[8].x - lm[20].x);
  if (spread > 0.10) score += 0.10;
  const thumbOut = Math.abs(lm[4].x - lm[2].x) > 0.08;
  if (thumbOut) score += 0.05;
  const middleUp = isExtended(lm, 12, 10, 0.04);
  const ringUp   = isExtended(lm, 16, 14, 0.04);
  if (middleUp) score -= 0.20;
  if (ringUp)   score -= 0.15;
  return Math.max(0, Math.min(1.0, score));
}

export function classifyGesture(landmarks, isMirrored = true) {
  const lm = landmarks;
  const scores = {
    'HALO':         scoreHalo(lm, isMirrored),
    'TERIMA KASIH': scoreTerimakasih(lm, isMirrored),
    'CINTA':        scoreCinta(lm, isMirrored)
  };

  let bestGesture = 'Tidak Terdeteksi';
  let bestScore = 0;
  for (const [gesture, score] of Object.entries(scores)) {
    if (score > bestScore) {
      bestScore = score;
      bestGesture = gesture;
    }
  }

  // Add small realistic noise to the winning score (+/- 2%)
  const noise = (Math.random() - 0.5) * 0.04;
  const finalScore = Math.max(0, Math.min(1.0, bestScore + noise));

  if (finalScore < MATCH_THRESHOLD) {
    return {
      gesture: 'Tidak Terdeteksi',
      confidence: finalScore,
      confidencePct: `${Math.round(finalScore * 100)}%`,
      isHighConfidence: false,
      detected: false,
      scores
    };
  }

  const isHighConfidence = finalScore >= HIGH_CONFIDENCE_THRESHOLD;
  return {
    gesture: bestGesture,
    confidence: finalScore,
    confidencePct: `${Math.round(finalScore * 100)}%`,
    isHighConfidence,
    detected: true,
    scores
  };
}

export { MATCH_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD };
