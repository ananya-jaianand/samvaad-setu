import torch
from transformers import pipeline
import time
from typing import Dict, Any

from .config import MODEL_NAME, SENTIMENT_CLASSES, HYPOTHESIS_TEMPLATE

class TextSentimentClassifier:
    def __init__(self):
        # Determine device (MPS for Apple Silicon, CUDA for NVIDIA, fallback to CPU)
        self.device = "cpu"
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
            
        print(f"Loading sentiment model {MODEL_NAME} on {self.device}...")
        
        # Load zero-shot classification pipeline
        self.classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=self.device
        )
        print("Sentiment model loaded successfully.")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze the text and return probabilities for the 6 sentiment classes.
        """
        start_time = time.time()
        
        # multi_label=False ensures scores sum to 1.0 for the provided classes.
        result = self.classifier(
            text,
            candidate_labels=SENTIMENT_CLASSES,
            hypothesis_template=HYPOTHESIS_TEMPLATE,
            multi_label=False
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Map labels to their confidence scores
        scores = {label: round(score, 4) for label, score in zip(result['labels'], result['scores'])}
        
        # Determine dominant emotion (the first one since pipeline sorts by score)
        dominant_label = result['labels'][0]
        dominant_score = result['scores'][0]
        
        return {
            "dominant_label": dominant_label,
            "dominant_score": round(dominant_score, 4),
            "all_scores": scores,
            "latency_ms": round(latency_ms, 2)
        }
