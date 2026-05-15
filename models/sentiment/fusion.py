import time
from typing import Dict, Any, Optional

from .config import SENTIMENT_CLASSES, HIGH_DISTRESS_THRESHOLD
from .text_sentiment import TextSentimentClassifier
from .prosodic_features import ProsodicSentimentExtractor

class SentimentFusionModel:
    def __init__(self, text_weight: float = 0.65, prosodic_weight: float = 0.35):
        """
        Initialize the fusion model that combines text and prosodic sentiment.
        
        Args:
            text_weight: Weight given to text-based sentiment (default 0.65)
            prosodic_weight: Weight given to audio-based sentiment (default 0.35)
        """
        self.text_weight = text_weight
        self.prosodic_weight = prosodic_weight
        
        # We ensure they sum to 1.0
        total = self.text_weight + self.prosodic_weight
        self.text_weight /= total
        self.prosodic_weight /= total
        
        print(f"Initializing Sentiment Fusion Model (Text: {self.text_weight:.2f}, Prosodic: {self.prosodic_weight:.2f})")
        
        self.text_classifier = TextSentimentClassifier()
        self.prosodic_extractor = ProsodicSentimentExtractor()
        
    def analyze(self, text: str, audio_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze both text and audio and return a fused sentiment score.
        """
        start_time = time.time()
        
        # 1. Get Text Sentiment
        text_result = self.text_classifier.analyze(text)
        
        # 2. Get Prosodic Sentiment (if audio provided)
        prosodic_result = None
        if audio_path:
            try:
                prosodic_result = self.prosodic_extractor.analyze(audio_path)
            except Exception as e:
                print(f"Warning: Failed to extract prosodic features: {e}")
        
        # 3. Fuse Scores
        fused_scores = {}
        for label in SENTIMENT_CLASSES:
            t_score = text_result["all_scores"].get(label, 0.0)
            
            if prosodic_result:
                p_score = prosodic_result["all_scores"].get(label, 0.0)
                fused_scores[label] = round((t_score * self.text_weight) + (p_score * self.prosodic_weight), 4)
            else:
                fused_scores[label] = t_score
                
        # 4. Determine dominant fused emotion
        dominant_label = max(fused_scores, key=fused_scores.get)
        dominant_score = fused_scores[dominant_label]
        
        # 5. Check if escalation is needed based on distress/fear/anger
        is_high_distress = False
        distress_aggregate = fused_scores.get("distress", 0.0) + (fused_scores.get("fear", 0.0) * 0.8) + (fused_scores.get("anger", 0.0) * 0.5)
        if distress_aggregate >= HIGH_DISTRESS_THRESHOLD:
            is_high_distress = True
            
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "dominant_label": dominant_label,
            "dominant_score": float(dominant_score),
            "is_high_distress": is_high_distress,
            "distress_aggregate": round(distress_aggregate, 4),
            "all_scores": fused_scores,
            "components": {
                "text": text_result["all_scores"],
                "prosodic": prosodic_result["all_scores"] if prosodic_result else None
            },
            "latency_ms": round(latency_ms, 2)
        }
