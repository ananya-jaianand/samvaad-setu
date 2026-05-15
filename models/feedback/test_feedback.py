import json
from .feedback_store import FeedbackStore

def main():
    print("Testing Feedback Store...")
    
    # Initialize the store
    store = FeedbackStore(storage_dir="data/datasets/test_feedback_dir")
    
    # Sample interactions
    sample_1 = {
        "transcript": "ನನ್ನ ಮನೆಯಲ್ಲಿ ನೀರು ಬರುತ್ತಿಲ್ಲ",
        "detected_language": "kannada",
        "district": "Bengaluru Urban",
        "intent": "water_supply_complaint",
        "sentiment_label": "distress",
        "verification_state": "correct",
        "agent_correction": None
    }
    
    sample_2 = {
        "transcript": "Power cut since morning",
        "detected_language": "english",
        "district": "Mysuru",
        "intent": "other_grievance",
        "sentiment_label": "anger",
        "verification_state": "incorrect",
        "agent_correction": "electricity_outage"
    }
    
    print("\nSaving Sample 1...")
    store.save_interaction(sample_1)
    
    print("Saving Sample 2...")
    store.save_interaction(sample_2)
    
    print("\nRetrieving all feedback data...")
    all_data = store.get_all_feedback()
    print(f"Total records retrieved: {len(all_data)}")
    
    print("\nFeedback Statistics:")
    print(json.dumps(store.get_stats(), indent=2))
    
    print("\nFirst record from store:")
    print(json.dumps(all_data[0], indent=2))
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
