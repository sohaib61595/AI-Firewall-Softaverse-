"""
train_model.py
==============
Downloads multiple prompt-injection / jailbreak datasets from Hugging Face,
blends them with a large synthetic multi-class corpus, then trains a
high-accuracy TF-IDF + Logistic Regression pipeline.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)
from sklearn.model_selection import (
    cross_val_score, StratifiedKFold, train_test_split, GridSearchCV, learning_curve, cross_validate
)
from sklearn.pipeline import Pipeline

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.utils import preprocess
from backend.synthetic_data import SYNTHETIC
from backend.unseen_test_set import UNSEEN_SAFE, UNSEEN_JAILBREAK

# ---- Paths ------------------------------------------------------------------
OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(OUT_DIR, "model.pkl")
DATA_DIR = os.path.join(os.path.dirname(OUT_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---- 2. Local Dataset Loader ------------------------------------------------

def load_local_dataset(local_path: str) -> pd.DataFrame:
    if os.path.exists(local_path):
        print(f"   [LOAD] {local_path}")
        try:
            if local_path.endswith('.csv'):
                return pd.read_csv(local_path)
            return pd.read_parquet(local_path)
        except Exception as e:
            print(f"   [WARN] Could not load {local_path}: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

# ---- 3. Build unified dataset -----------------------------------------------

def build_dataset():
    texts, labels = [], []

    # 3a. deepset/prompt-injections
    deepset_path = os.path.join(DATA_DIR, "deepset_prompt_injections.csv")
    if not os.path.exists(deepset_path):
        deepset_path = os.path.join(DATA_DIR, "deepset_prompt_injections.parquet")
    df = load_local_dataset(deepset_path)
    if not df.empty:
        for _, row in df.iterrows():
            t = str(row.get("text", "")).strip()
            lbl = int(row.get("label", 0))
            if t:
                labels.append("SAFE" if lbl == 0 else "JAILBREAK")
                texts.append(t)
        print(f"   deepset dataset: {len(texts)} rows added")

    # 3b. jackhhao/jailbreak-classification (if it exists locally)
    before = len(texts)
    jackhhao_path = os.path.join(DATA_DIR, "jackhhao_jailbreak.csv")
    df2 = load_local_dataset(jackhhao_path)
    if not df2.empty:
        for _, row in df2.iterrows():
            col = "prompt" if "prompt" in df2.columns else df2.columns[0]
            lbl_col = "type" if "type" in df2.columns else df2.columns[-1]
            t = str(row.get(col, "")).strip()
            lbl_raw = str(row.get(lbl_col, "benign")).lower()
            if t:
                labels.append("SAFE" if "benign" in lbl_raw else "JAILBREAK")
                texts.append(t)
        print(f"   jackhhao dataset: {len(texts) - before} rows added")

    # 3c. rubend18/ChatGPT-Jailbreak-Prompts
    before = len(texts)
    rubend_path = os.path.join(DATA_DIR, "rubend18_jailbreak.csv")
    if not os.path.exists(rubend_path):
        rubend_path = os.path.join(DATA_DIR, "rubend18_jailbreak.parquet")
    df3 = load_local_dataset(rubend_path)
    if not df3.empty:
        text_col = df3.columns[0]
        for _, row in df3.iterrows():
            t = str(row.get(text_col, "")).strip()
            if t and len(t) > 20:
                labels.append("JAILBREAK")
                texts.append(t)
        print(f"   rubend18 dataset: {len(texts) - before} rows added")

    # 3e. hf_safe_prompts (alpaca)
    before = len(texts)
    hf_safe = os.path.join(DATA_DIR, "hf_safe_prompts.csv")
    df_safe = load_local_dataset(hf_safe)
    if not df_safe.empty:
        for _, row in df_safe.iterrows():
            t = str(row.get("text", "")).strip()
            if t:
                labels.append("SAFE")
                texts.append(t)
        print(f"   hf_safe_prompts: {len(texts) - before} rows added")

    # 3f. hf_jailbreaks (rubend18 updated)
    before = len(texts)
    hf_jb = os.path.join(DATA_DIR, "hf_jailbreaks.csv")
    df_jb = load_local_dataset(hf_jb)
    if not df_jb.empty:
        for _, row in df_jb.iterrows():
            t = str(row.get("text", "")).strip()
            if t:
                labels.append("JAILBREAK")
                texts.append(t)
        print(f"   hf_jailbreaks: {len(texts) - before} rows added")

    # 3g. synthetic_payloads (missing edge cases)
    before = len(texts)
    hf_payloads = os.path.join(DATA_DIR, "synthetic_payloads.csv")
    df_payloads = load_local_dataset(hf_payloads)
    if not df_payloads.empty:
        for _, row in df_payloads.iterrows():
            t = str(row.get("text", "")).strip()
            lbl = str(row.get("label", "JAILBREAK")).strip()
            if t:
                labels.append(lbl)
                texts.append(t)
        print(f"   synthetic_payloads: {len(texts) - before} rows added")

    # 3d. Synthetic multi-class corpus (NO AUGMENTATION YET)
    before = len(texts)
    for cat, samples in SYNTHETIC.items():
        for s in samples:
            texts.append(s)
            labels.append(cat)

    print(f"   Synthetic corpus: {len(texts) - before} rows added")

    print("\n   -- Dataset Breakdown -------------------------------")
    for cat in sorted(set(labels)):
        n = labels.count(cat)
        bar = "#" * (n // 10)
        print(f"   {cat:<22}  {n:>5}  {bar}")
    print(f"   {'TOTAL':<22}  {len(labels):>5}")
    print("   ----------------------------------------------------")

    return texts, labels


def augment_training_data(X_train, y_train):
    """Augment ONLY the training data to prevent leakage into the test set."""
    from backend.synthetic_data import get_synthetic_expansions
    
    aug_x, aug_y = [], []
    for x, y in zip(X_train, y_train):
        aug_x.append(x)
        aug_y.append(y)
        if y not in ("SAFE",):
            aug_x.append(x + " Please do this immediately.")
            aug_y.append(y)
            aug_x.append(x + " This is very important.")
            aug_y.append(y)
            
    # Add combinatorial expansions here to ensure they never leak into X_test
    print("   [INFO] Adding combinatorial synthetic data to training set...")
    expanded = get_synthetic_expansions()
    for cat, samples in expanded.items():
        for s in samples:
            aug_x.append(s)
            aug_y.append(cat)
            
    return aug_x, aug_y


def plot_learning_curve(pipeline, X, y):
    print("\n[INFO] Generating learning curve...")
    train_sizes, train_scores, test_scores = learning_curve(
        pipeline, X, y, cv=5, n_jobs=-1, train_sizes=np.linspace(0.1, 1.0, 5), scoring="accuracy"
    )
    
    train_scores_mean = np.mean(train_scores, axis=1)
    test_scores_mean = np.mean(test_scores, axis=1)
    
    plt.figure()
    plt.title("Learning Curve (AI Firewall)")
    plt.xlabel("Training examples")
    plt.ylabel("Accuracy")
    plt.grid()
    plt.plot(train_sizes, train_scores_mean, 'o-', color="r", label="Training score")
    plt.plot(train_sizes, test_scores_mean, 'o-', color="g", label="Cross-validation score")
    plt.legend(loc="best")
    
    plot_path = os.path.join(OUT_DIR, "learning_curve.png")
    plt.savefig(plot_path)
    print(f"[DONE] Saved learning curve to {plot_path}")


# ---- 4. Train ---------------------------------------------------------------

def main():
    print("\n" + "=" * 56)
    print("   AI Firewall - Prompt Injection Model Training")
    print("=" * 56)

    print("\n[1/5] Building dataset...")
    texts, labels = build_dataset()

    X_train_raw, X_test, y_train_raw, y_test = train_test_split(
        texts, labels, test_size=0.15, random_state=42, stratify=labels
    )
    
    # Apply augmentation ONLY to training data (Hygiene Fix)
    X_train, y_train = augment_training_data(X_train_raw, y_train_raw)

    print(f"\n[2/5] Training pipeline on {len(X_train)} samples (after augmentation)...")
    
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                preprocessor=preprocess,
                ngram_range=(1, 4),
                max_features=50_000,
                sublinear_tf=True,
                min_df=1,
                analyzer="word",
            ),
        ),
        (
            "clf",
            LogisticRegression(
                random_state=42,
                class_weight="balanced",
                solver="lbfgs",
                max_iter=2000,
            ),
        ),
    ])
    
    # Grid Search for C parameter
    print("\n[3/5] Running GridSearchCV for LogisticRegression C parameter...")
    param_grid = {
        'clf__C': [0.1, 1.0, 5.0, 10.0]
    }
    grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='accuracy', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    
    best_pipeline = grid_search.best_estimator_
    print(f"      Best C value chosen: {grid_search.best_params_['clf__C']}")

    print("\n[4/5] Evaluating on held-out test set (15%)...")
    y_train_pred = best_pipeline.predict(X_train)
    y_test_pred = best_pipeline.predict(X_test)
    
    train_acc = accuracy_score(y_train, y_train_pred) * 100
    test_acc = accuracy_score(y_test, y_test_pred) * 100
    
    print(f"\nTrain Accuracy: {train_acc:.1f}%")
    print(f"Test Accuracy : {test_acc:.1f}%")
    if abs(train_acc - test_acc) > 5.0:
        print("      [WARN] Gap between train and test is > 5 points. Model may be overfitting.")

    print(f"\n{classification_report(y_test, y_test_pred, digits=3)}")
    
    print("Confusion Matrix (Test Set):")
    print(confusion_matrix(y_test, y_test_pred))

    # 5-fold stratified cross-validation on full UN-augmented dataset
    print("\n[5/5] Running 5-fold stratified cross-validation (Full metrics)...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
    cv_results = cross_validate(best_pipeline, texts, labels, cv=cv, scoring=scoring, n_jobs=-1)
    
    cv_acc_mean = cv_results['test_accuracy'].mean() * 100
    cv_acc_std  = cv_results['test_accuracy'].std()  * 100
    
    # Plot learning curve
    plot_learning_curve(best_pipeline, texts, labels)
    
    # Unseen generalization test
    print("\n--- UNSEEN GENERALIZATION TEST ---")
    unseen_texts = UNSEEN_SAFE + UNSEEN_JAILBREAK
    unseen_labels = ["SAFE"] * len(UNSEEN_SAFE) + ["JAILBREAK"] * len(UNSEEN_JAILBREAK)
    unseen_preds = best_pipeline.predict(unseen_texts)
    unseen_acc = accuracy_score(unseen_labels, unseen_preds) * 100
    print(f"Accuracy on unseen phrasing: {unseen_acc:.1f}%")
    print(classification_report(unseen_labels, unseen_preds))
    print("Confusion Matrix (Unseen):")
    print(confusion_matrix(unseen_labels, unseen_preds))

    # ── Final accuracy banner ──────────────────────────────────────────────
    print("\n" + "=" * 56)
    print(f"  [OK] TEST SET ACCURACY      :  {test_acc:.1f}%")
    print(f"  [OK] CROSS-VAL ACCURACY     :  {cv_acc_mean:.1f}%  (+/-{cv_acc_std:.1f}%)")
    print(f"  [OK] UNSEEN TEST ACCURACY   :  {unseen_acc:.1f}%")
    grade = "EXCELLENT" if cv_acc_mean >= 95 else "GOOD" if cv_acc_mean >= 88 else "FAIR"
    print(f"  [OK] GRADE                  :  {grade}")
    print("=" * 56)

    joblib.dump(best_pipeline, MODEL_PATH)
    print(f"\n[DONE] Pipeline saved -> {MODEL_PATH}\n")


if __name__ == "__main__":
    main()
