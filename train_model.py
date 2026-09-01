"""
train_model.py
---------------
End-to-end training pipeline for the Fake Internship Detector.

Pipeline (Engineering workflow):
  1. Load raw EMSCAD dataset (data/dataset.csv)
  2. Build a single 'raw_text' field per posting (title + company_profile +
     description + requirements + benefits) -> mirrors what a user pastes
     into the Streamlit app as one blob.
  3. Preprocess text (preprocess.py) for TF-IDF.
  4. Engineer structured, explainable features (feature_engineering.py).
  5. Combine TF-IDF (sparse) + scaled structured features -> single matrix.
  6. Stratified train/test split (80/20).
  7. Train 3 candidate models: Logistic Regression, Random Forest, Linear
     SVM (calibrated for probabilities). All use class_weight='balanced'
     because the dataset is heavily imbalanced (~4.8% fraudulent).
  8. Evaluate all 3 on the held-out test set: accuracy, precision, recall,
     F1 (both macro and for the fraudulent class specifically), confusion
     matrix.
  9. Select the best model by F1-score on the fraudulent (minority) class
     -- the metric that actually matters for this problem, since a model
     that just predicts "real" for everything gets ~95% accuracy but is
     useless.
  10. Save: best model, TF-IDF vectorizer, structured-feature scaler,
      metrics table (JSON + printed), confusion matrix plots, and a
      model-comparison bar chart.

No numbers in this script are hand-typed anywhere else in the project --
README.md and the Streamlit app read the same models/metrics.json file
that this script produces, so all reported numbers come from one real
training run.
"""

import json
import time
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.sparse import hstack, csr_matrix
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                              precision_score, recall_score,
                              classification_report)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from preprocess import clean_text, combine_fields
from feature_engineering import (STRUCTURED_FEATURE_NAMES,
                                  extract_structured_features,
                                  structured_features_to_vector)

warnings.filterwarnings("ignore")

DATA_PATH = "data/dataset.csv"
MODELS_DIR = "models"
OUTPUTS_DIR = "outputs"
RANDOM_STATE = 42
TFIDF_MAX_FEATURES = 4000

TEXT_FIELDS = ["title", "company_profile", "description", "requirements",
               "benefits"]


def load_data():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["fraudulent"])
    df["fraudulent"] = df["fraudulent"].astype(int)

    df["raw_text"] = df.apply(lambda r: combine_fields(r, TEXT_FIELDS), axis=1)
    df = df[df["raw_text"].str.strip().str.len() > 0].reset_index(drop=True)
    return df


def build_features(df, vectorizer=None, scaler=None, fit=True):
    """Build the combined (TF-IDF + structured) feature matrix.
    If fit=True, fits a new vectorizer/scaler; else reuses the ones passed
    in (used for the test split so there's no data leakage)."""

    cleaned = df["raw_text"].apply(clean_text)

    if fit:
        vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES,
                                      ngram_range=(1, 2), min_df=2)
        tfidf_matrix = vectorizer.fit_transform(cleaned)
    else:
        tfidf_matrix = vectorizer.transform(cleaned)

    struct_rows = []
    for _, row in df.iterrows():
        feats = extract_structured_features(
            row["raw_text"],
            telecommuting=row.get("telecommuting", 0) or 0,
            has_company_logo=row.get("has_company_logo", 0) or 0,
            has_questions=row.get("has_questions", 0) or 0,
        )
        struct_rows.append(structured_features_to_vector(feats))
    struct_matrix = np.vstack(struct_rows)

    if fit:
        scaler = StandardScaler()
        struct_scaled = scaler.fit_transform(struct_matrix)
    else:
        struct_scaled = scaler.transform(struct_matrix)

    combined = hstack([tfidf_matrix, csr_matrix(struct_scaled)]).tocsr()
    return combined, vectorizer, scaler


def evaluate(name, model, X_test, y_test):
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec_macro = precision_score(y_test, y_pred, average="macro", zero_division=0)
    rec_macro = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)

    prec_fraud = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    rec_fraud = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1_fraud = f1_score(y_test, y_pred, pos_label=1, zero_division=0)

    cm = confusion_matrix(y_test, y_pred)

    report = {
        "model": name,
        "accuracy": acc,
        "precision_macro": prec_macro,
        "recall_macro": rec_macro,
        "f1_macro": f1_macro,
        "precision_fraudulent_class": prec_fraud,
        "recall_fraudulent_class": rec_fraud,
        "f1_fraudulent_class": f1_fraud,
        "confusion_matrix": cm.tolist(),
    }
    print(f"\n===== {name} =====")
    print(f"Accuracy:              {acc:.4f}")
    print(f"F1 (macro):            {f1_macro:.4f}")
    print(f"F1 (fraudulent class): {f1_fraud:.4f}")
    print(f"Precision (fraud):     {prec_fraud:.4f}   Recall (fraud): {rec_fraud:.4f}")
    print(classification_report(y_test, y_pred, target_names=["Legitimate", "Fraudulent"], zero_division=0))
    return report, cm


def plot_confusion_matrix(cm, name, path):
    plt.figure(figsize=(4.5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Legitimate", "Fraudulent"],
                yticklabels=["Legitimate", "Fraudulent"])
    plt.title(f"Confusion Matrix - {name}")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def plot_model_comparison(reports, path):
    names = [r["model"] for r in reports]
    metrics = ["accuracy", "f1_macro", "f1_fraudulent_class"]
    labels = ["Accuracy", "F1 (macro)", "F1 (fraudulent class)"]

    x = np.arange(len(names))
    width = 0.25
    plt.figure(figsize=(8, 5))
    for i, (m, lab) in enumerate(zip(metrics, labels)):
        vals = [r[m] for r in reports]
        plt.bar(x + i * width, vals, width, label=lab)
    plt.xticks(x + width, names)
    plt.ylim(0, 1.05)
    plt.ylabel("Score")
    plt.title("Model Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main():
    t0 = time.time()
    print("Loading dataset...")
    df = load_data()
    print(f"Loaded {len(df)} postings "
          f"({df['fraudulent'].sum()} fraudulent, "
          f"{(df['fraudulent'] == 0).sum()} legitimate)")

    train_df, test_df = train_test_split(
        df, test_size=0.2, stratify=df["fraudulent"], random_state=RANDOM_STATE
    )
    print(f"Train size: {len(train_df)}   Test size: {len(test_df)}")

    print("Building features (TF-IDF + structured)...")
    X_train, vectorizer, scaler = build_features(train_df, fit=True)
    X_test, _, _ = build_features(test_df, vectorizer=vectorizer,
                                   scaler=scaler, fit=False)
    y_train = train_df["fraudulent"].values
    y_test = test_df["fraudulent"].values
    print(f"Feature matrix shape: train={X_train.shape} test={X_test.shape}")

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE),
        "Random Forest": RandomForestClassifier(
            n_estimators=250, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=-1),
        "Linear SVM": CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", random_state=RANDOM_STATE,
                      max_iter=5000),
            cv=3),
    }

    reports = []
    cms = {}
    fitted_models = {}
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        fitted_models[name] = model
        report, cm = evaluate(name, model, X_test, y_test)
        reports.append(report)
        cms[name] = cm

        safe_name = name.lower().replace(" ", "_")
        plot_confusion_matrix(cm, name, f"{OUTPUTS_DIR}/confusion_matrix_{safe_name}.png")

    # main confusion matrix output (best model, filled in after selection)
    best_report = max(reports, key=lambda r: r["f1_fraudulent_class"])
    best_name = best_report["model"]
    best_model = fitted_models[best_name]
    print(f"\n>>> Best model selected: {best_name} "
          f"(F1 on fraudulent class = {best_report['f1_fraudulent_class']:.4f}) <<<")

    plot_confusion_matrix(cms[best_name], best_name,
                           f"{OUTPUTS_DIR}/confusion_matrix.png")
    plot_model_comparison(reports, f"{OUTPUTS_DIR}/model_comparison.png")

    joblib.dump(best_model, f"{MODELS_DIR}/model.pkl")
    joblib.dump(vectorizer, f"{MODELS_DIR}/vectorizer.pkl")
    joblib.dump(scaler, f"{MODELS_DIR}/scaler.pkl")

    metrics_out = {
        "dataset_size": int(len(df)),
        "train_size": int(len(train_df)),
        "test_size": int(len(test_df)),
        "fraudulent_count": int(df["fraudulent"].sum()),
        "legitimate_count": int((df["fraudulent"] == 0).sum()),
        "best_model": best_name,
        "structured_feature_names": STRUCTURED_FEATURE_NAMES,
        "tfidf_max_features": TFIDF_MAX_FEATURES,
        "all_model_reports": reports,
        "training_time_seconds": round(time.time() - t0, 1),
    }
    with open(f"{MODELS_DIR}/metrics.json", "w") as f:
        json.dump(metrics_out, f, indent=2)

    print(f"\nSaved model -> {MODELS_DIR}/model.pkl")
    print(f"Saved vectorizer -> {MODELS_DIR}/vectorizer.pkl")
    print(f"Saved scaler -> {MODELS_DIR}/scaler.pkl")
    print(f"Saved metrics -> {MODELS_DIR}/metrics.json")
    print(f"Saved plots -> {OUTPUTS_DIR}/")
    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
