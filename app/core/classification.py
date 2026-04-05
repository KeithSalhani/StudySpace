import logging
from typing import Callable, Dict, List, Optional

from transformers import pipeline

logger = logging.getLogger(__name__)

class Classifier:
    def __init__(self):
        self._classifier: Optional[Callable] = None

    def _get_classifier(self):
        if self._classifier is None:
            logger.info("Initializing zero-shot classifier pipeline")
            self._classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,
            )
        return self._classifier
        
    def classify(self, text: str, candidate_labels: List[str]) -> Dict:
        """
        Classify text using zero-shot classification
        
        Args:
            text: Text to classify
            candidate_labels: List of labels to predict
            
        Returns:
            Dictionary containing labels and scores
        """
        # Truncate text if too long for the model (simple truncation)
        # BART model max length is usually 1024 tokens, taking first 2000 chars as approximation
        text_to_classify = text[:2000]
        classifier = self._get_classifier()
        return classifier(text_to_classify, candidate_labels)

# Standalone usage for testing
if __name__ == "__main__":
    classifier = Classifier()
    
    sequence_to_classify = '''
    Chapter 5
    Advanced Encryption Standard
    Finite Field Arithmetic
    ... (rest of the example text) ...
    '''
    
    candidate_labels = ['Forensics', 'Machine Learning', 'Security', 'Final Year Project']
    print(classifier.classify(sequence_to_classify, candidate_labels))
