# models/sentiment/config.py

# Model configuration
MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# 6-class emotion taxonomy
SENTIMENT_CLASSES = [
    "distress",
    "anger",
    "fear",
    "urgency",
    "confusion",
    "calm"
]

# Multilingual Hypothesis Template for zero-shot classification
# This helps the model understand what we are asking in multiple languages.
HYPOTHESIS_TEMPLATE = "The emotion of this text is {}."

# Confidence threshold to flag high distress (for escalation)
HIGH_DISTRESS_THRESHOLD = 0.70
