# models/intent/config.py

# Base model for zero-shot intent
MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# The 13 grievance categories from the Karnataka taxonomy
INTENT_CLASSES = [
    "water_supply_complaint",
    "electricity_outage",
    "road_damage",
    "sanitation_garbage",
    "property_tax_query",
    "birth_death_certificate",
    "ration_card_issue",
    "pension_scheme",
    "police_complaint",
    "health_facility",
    "education_school",
    "land_records",
    "other_grievance"
]

HYPOTHESIS_TEMPLATE = "The intent of this citizen's grievance is {}."

# Localized Ambiguity Dictionary (Kannada/Hinglish/English)
# Maps known ambiguous terms to the list of intents they could represent
LOCALIZED_AMBIGUITY_DICT = {
    # Kannada
    "neeru": ["water_supply_complaint", "sanitation_garbage"], # Water (supply issue vs contaminated water/drainage)
    "kasa": ["sanitation_garbage", "road_damage", "health_facility"], # Garbage/weeds
    "current": ["electricity_outage", "other_grievance"], # Power cut vs street light
    "beli": ["electricity_outage", "other_grievance"], # Light
    "rasta": ["road_damage", "sanitation_garbage"], # Road (pothole vs blocked by garbage)
    "gundi": ["road_damage", "water_supply_complaint"], # Pothole vs open manhole
    
    # English/Hinglish
    "water": ["water_supply_complaint", "sanitation_garbage"],
    "drain": ["sanitation_garbage", "water_supply_complaint", "road_damage"],
    "light": ["electricity_outage", "other_grievance"],
    "bill": ["electricity_outage", "water_supply_complaint", "property_tax_query"]
}

# Threshold for requiring clarification
# If ambiguity score > this threshold, force the verification engine to ask a clarification question
AMBIGUITY_THRESHOLD = 0.65
