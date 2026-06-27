"""
train_model.py
==============
Downloads multiple prompt-injection / jailbreak datasets from Hugging Face,
blends them with a large synthetic multi-class corpus, then trains a
high-accuracy TF-IDF + Logistic Regression pipeline.

Run ONCE before starting the server:
    python -m backend.train_model

Outputs:
    backend/model.pkl   -- full sklearn Pipeline (vectorizer + classifier)

Datasets used (all public, no auth required):
    1. deepset/prompt-injections       (binary: safe vs injection)
    2. jackhhao/jailbreak-classification (binary: benign vs jailbreak)
    3. rubend18/ChatGPT-Jailbreak-Prompts (jailbreak prompts)
"""

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from backend.utils import preprocess

# ---- Paths ------------------------------------------------------------------
OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(OUT_DIR, "model.pkl")
DATA_DIR = os.path.join(os.path.dirname(OUT_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)




# ---- 1. Synthetic multi-class data ------------------------------------------

from backend.synthetic_data import SYNTHETIC


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

    # 3d. Synthetic multi-class corpus (augmented)
    before = len(texts)
    for cat, samples in SYNTHETIC.items():
        for s in samples:
            texts.append(s)
            labels.append(cat)
            # Augmentation: add slight variations for attack classes
            if cat not in ("SAFE",):
                texts.append(s + " Please do this immediately.")
                labels.append(cat)
                texts.append(s + " This is very important.")
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


# ---- 4. Train ---------------------------------------------------------------

def main():
    print("\n" + "=" * 56)
    print("   AI Firewall - Prompt Injection Model Training")
    print("=" * 56)

    print("\n[1/4] Building dataset...")
    texts, labels = build_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.15, random_state=42, stratify=labels
    )

    print(f"\n[2/4] Training pipeline on {len(X_train)} samples...")
    print("      Model : TF-IDF (word 1-3 gram)  +  Logistic Regression")
    print("      Vocab : 30,000 features  |  sublinear_tf=True")

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
                C=5.0,
                max_iter=2000,
                random_state=42,
                class_weight="balanced",
                solver="lbfgs",
            ),
        ),
    ])
    pipeline.fit(X_train, y_train)

    print("\n[3/4] Evaluating on held-out test set (15%)...")
    y_pred = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred) * 100

    print(f"\n{classification_report(y_test, y_pred, digits=3)}")

    # 5-fold stratified cross-validation on full dataset
    print("[4/4] Running 5-fold stratified cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, texts, labels, cv=cv, scoring="accuracy", n_jobs=-1)  # type: ignore
    cv_mean = cv_scores.mean() * 100
    cv_std  = cv_scores.std()  * 100

    # ── Final accuracy banner ──────────────────────────────────────────────
    print("\n" + "=" * 56)
    print(f"  [OK] TEST SET ACCURACY      :  {test_acc:.1f}%")
    print(f"  [OK] CROSS-VAL ACCURACY     :  {cv_mean:.1f}%  (+/-{cv_std:.1f}%)")
    print(f"  [OK] CROSS-VAL FOLD SCORES  :  " +
          "  ".join(f"{s*100:.1f}%" for s in cv_scores))
    grade = "EXCELLENT" if cv_mean >= 95 else "GOOD" if cv_mean >= 88 else "FAIR"
    print(f"  [OK] GRADE                  :  {grade}")
    print("=" * 56)

    joblib.dump(pipeline, MODEL_PATH)
    print(f"\n[DONE] Pipeline saved -> {MODEL_PATH}\n")


if __name__ == "__main__":
    main()
