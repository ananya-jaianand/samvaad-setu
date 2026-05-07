import time
import os
from typing import Dict, Any

from .config import SENTIMENT_CLASSES

class ProsodicSentimentExtractor:
    def __init__(self):
        print("Initializing openSMILE prosodic extractor...")
        try:
            import opensmile
            self.smile = opensmile.Smile(
                feature_set=opensmile.FeatureSet.eGeMAPSv02,
                feature_level=opensmile.FeatureLevel.Functionals,
            )
            self._available = True
            print("openSMILE loaded successfully.")
        except ImportError:
            print("WARNING: opensmile package not found. Prosodic features will be simulated.")
            self._available = False

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio file and return sentiment scores based on prosodic features.
        """
        start_time = time.time()
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        scores = {label: 0.0 for label in SENTIMENT_CLASSES}

        if self._available:
            # Process the audio file to extract 88 eGeMAPS functionals
            df = self.smile.process_file(audio_path)
            
            # Extract key features for our heuristic mapping
            # (In a production system, these would feed into a trained classifier/regressor)
            try:
                loudness = df['loudness_sma3_amean'].iloc[0]
                pitch = df['F0semitoneFrom27.5Hz_sma3nz_amean'].iloc[0]
                pitch_var = df['F0semitoneFrom27.5Hz_sma3nz_stddevNorm'].iloc[0]
                jitter = df['jitterLocal_sma3nz_amean'].iloc[0]
                shimmer = df['shimmerLocaldB_sma3nz_amean'].iloc[0]
                
                # Heuristic mapping based on typical acoustic correlates of emotion:
                
                # Anger: High loudness, high pitch
                scores["anger"] = min(1.0, (loudness / 2.0) + (pitch / 40.0))
                
                # Distress/Fear: High jitter/shimmer (voice trembling), high pitch variance
                scores["distress"] = min(1.0, (jitter * 10) + (shimmer * 5) + pitch_var)
                scores["fear"] = scores["distress"] * 0.9  # Correlated with distress
                
                # Urgency: High loudness, but less pitch variance than distress
                scores["urgency"] = min(1.0, loudness / 1.5)
                
                # Calm: Low loudness, low pitch variance
                scores["calm"] = max(0.0, 1.0 - (loudness + pitch_var * 2))
                
                # Confusion: Moderate values, often indicated by rising pitch at end (hard to capture with just functionals, so we keep it baseline)
                scores["confusion"] = 0.2
                
            except KeyError as e:
                print(f"Missing expected openSMILE feature: {e}")
                scores["calm"] = 1.0
        else:
            # Fallback if opensmile is not installed
            scores["calm"] = 1.0
            
        # Normalize scores to sum to 1.0 and convert to standard float
        total = float(sum(scores.values()))
        if total > 0:
            scores = {k: round(float(v) / total, 4) for k, v in scores.items()}
        else:
            scores = {k: 1.0/len(SENTIMENT_CLASSES) for k in SENTIMENT_CLASSES}
            
        latency_ms = (time.time() - start_time) * 1000
        
        # Determine dominant emotion
        dominant_label = max(scores, key=scores.get)
        dominant_score = scores[dominant_label]
        
        return {
            "dominant_label": dominant_label,
            "dominant_score": float(dominant_score),
            "all_scores": scores,
            "latency_ms": round(latency_ms, 2)
        }
