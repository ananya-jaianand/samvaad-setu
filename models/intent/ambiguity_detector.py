import torch
import time
import re
from typing import Dict, Any
from transformers import pipeline

try:
    from scipy.stats import entropy
except ImportError:
    # Fallback if scipy isn't available
    import math
    def entropy(pk):
        return -sum(p * math.log(p) for p in pk if p > 0)

from .config import MODEL_NAME, INTENT_CLASSES, HYPOTHESIS_TEMPLATE, LOCALIZED_AMBIGUITY_DICT, AMBIGUITY_THRESHOLD

class SemanticAmbiguityDetector:
    def __init__(self):
        self.device = "cpu"
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
            
        print(f"Loading intent model {MODEL_NAME} for ambiguity detection on {self.device}...")
        
        self.classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=self.device
        )
        print("Ambiguity Detector ready.")

    def analyze(self, transcript: str) -> Dict[str, Any]:
        """
        Analyzes the transcript to determine if the intent is ambiguous.
        Returns an ambiguity score from 0.0 to 1.0.
        """
        start_time = time.time()
        transcript_lower = transcript.lower()
        
        # 1. Dictionary Check (Localized Keyword Ambiguity)
        keyword_flags = []
        conflicting_intents = set()
        
        # Simple tokenization by word boundary (handles English/Hinglish and some Kannada spaces)
        words = re.findall(r'\b\w+\b', transcript_lower)
        
        for word in words:
            if word in LOCALIZED_AMBIGUITY_DICT:
                keyword_flags.append(word)
                conflicting_intents.update(LOCALIZED_AMBIGUITY_DICT[word])
                
        # 2. Mathematical Check (Shannon Entropy of Intent Probabilities)
        result = self.classifier(
            transcript,
            candidate_labels=INTENT_CLASSES,
            hypothesis_template=HYPOTHESIS_TEMPLATE,
            multi_label=False
        )
        
        scores = result['scores']
        labels = result['labels']
        
        # Calculate Normalized Shannon Entropy (0 to 1)
        # We only use the top 5 probabilities to focus the entropy on the leading candidates
        top_k = 5
        top_scores = scores[:top_k]
        
        # Re-normalize top k
        total_top = sum(top_scores)
        norm_top_scores = [s / total_top for s in top_scores]
        
        # Entropy calculation. Max entropy for k items is log(k)
        try:
            import numpy as np
            from scipy.stats import entropy as scipy_entropy
            raw_entropy = scipy_entropy(norm_top_scores)
            max_entropy = np.log(top_k)
        except ImportError:
            import math
            raw_entropy = -sum(p * math.log(p) for p in norm_top_scores if p > 0)
            max_entropy = math.log(top_k)
            
        normalized_entropy = raw_entropy / max_entropy if max_entropy > 0 else 0
        
        # Margin between top 1 and top 2 (smaller margin = higher ambiguity)
        margin = scores[0] - scores[1]
        margin_penalty = max(0, 0.2 - margin) * 2 # If margin < 0.2, penalize heavily
        
        # 3. Calculate Final Ambiguity Score
        # Base ambiguity is the entropy.
        base_score = normalized_entropy
        
        # If localized keywords are found, boost ambiguity significantly
        dict_boost = 0.0
        if keyword_flags:
            dict_boost = 0.3 # 30% boost if known ambiguous terms are used
            
            # If the top predicted intent is one of the conflicting intents, boost even more
            if labels[0] in conflicting_intents or labels[1] in conflicting_intents:
                dict_boost += 0.2
                
        final_ambiguity_score = min(1.0, base_score + dict_boost + margin_penalty)
        requires_clarification = final_ambiguity_score >= AMBIGUITY_THRESHOLD
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "transcript": transcript,
            "top_intent": labels[0],
            "top_intent_confidence": round(scores[0], 4),
            "secondary_intent": labels[1],
            "ambiguity_score": round(final_ambiguity_score, 4),
            "requires_clarification": bool(requires_clarification),
            "reasons": {
                "base_entropy": round(base_score, 4),
                "margin_penalty": round(margin_penalty, 4),
                "keywords_flagged": keyword_flags,
                "conflicting_intents": list(conflicting_intents) if keyword_flags else []
            },
            "latency_ms": round(latency_ms, 2)
        }
