"""
test_accuracy.py
================
Standalone script to test the trained AI Firewall model accuracy.
This script evaluates the saved model (backend/model.pkl) against
the data sources and computes the overall test accuracy percentage.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import joblib
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from backend.synthetic_data import SYNTHETIC
from backend.train_model import build_dataset

def main():
    print("========================================================")
    print("   AI Firewall - Standalone Accuracy Test")
    print("========================================================")

    model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}. Please run train_model.py first.")
        return

    print("\n[1/3] Loading saved model...")
    pipeline = joblib.load(model_path)

    print("\n[2/3] Loading evaluation data (this may take a moment)...")
    import sys, io
    # Suppress the verbose dataset building logs
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        texts, labels = build_dataset()
    finally:
        sys.stdout = original_stdout
    
    # We use a fixed random state to isolate the exact same test set 
    # that the model held out during training, ensuring no data leakage.
    _, X_test, _, y_test = train_test_split(
        texts, labels, test_size=0.15, random_state=42, stratify=labels
    )

    print(f"      Loaded {len(X_test)} unseen test samples.")

    print("\n[3/3] Running predictions and calculating accuracy...")
    y_pred = pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred) * 100
    
    print("\n========================================================")
    print(f"   FINAL MODEL ACCURACY : {acc:.2f}%")
    print("========================================================\n")
    
    print("Detailed Classification Report:\n")
    print(classification_report(y_test, y_pred, digits=3))

if __name__ == "__main__":
    main()
