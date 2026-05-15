import json
import os
import time
from typing import Dict, Any, List

class FeedbackStore:
    def __init__(self, storage_dir: str = "data/datasets"):
        """
        Initializes the Feedback Store to capture confirmed interactions as labeled data.
        
        Args:
            storage_dir: Directory to store the feedback JSONL files
        """
        self.storage_dir = storage_dir
        self.file_path = os.path.join(self.storage_dir, "labeled_feedback.jsonl")
        
        # Ensure the directory exists
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            
        print(f"Feedback store initialized at {self.file_path}")

    def save_interaction(self, data: Dict[str, Any]) -> bool:
        """
        Saves a single confirmed interaction or agent correction to the store.
        
        Expected fields in data:
        - transcript: str
        - detected_language: str
        - district: str
        - intent: str
        - sentiment_label: str
        - verification_state: str (correct / partially_correct / incorrect)
        - agent_correction: str (optional, what the human changed it to)
        """
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = time.time()
            
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Retrieves all captured feedback data for retraining.
        """
        if not os.path.exists(self.file_path):
            return []
            
        results = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line))
        except Exception as e:
            print(f"Error reading feedback: {e}")
            
        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns basic statistics about the captured data.
        """
        data = self.get_all_feedback()
        
        if not data:
            return {"total_records": 0}
            
        stats = {
            "total_records": len(data),
            "by_verification": {},
            "by_language": {}
        }
        
        for record in data:
            # Count by verification state
            v_state = record.get("verification_state", "unknown")
            stats["by_verification"][v_state] = stats["by_verification"].get(v_state, 0) + 1
            
            # Count by language
            lang = record.get("detected_language", "unknown")
            stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
            
        return stats
