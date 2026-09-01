"""
evaluate_model.py
------------------
Standalone evaluation / reporting script.

This does NOT retrain anything — it reloads the metrics.json produced by
train_model.py (real numbers from the actual training run) and prints a
clean report, plus confirms the saved plots exist. Useful for the Review 2
demo: run this to show the evaluation results without waiting for training.

Run train_model.py first if models/metrics.json does not exist yet.
"""

import json
import os
import sys

METRICS_PATH = "models/metrics.json"
OUTPUTS_DIR = "outputs"


def main():
    if not os.path.exists(METRICS_PATH):
        print(f"ERROR: {METRICS_PATH} not found. Run `python train_model.py` first.")
        sys.exit(1)

    with open(METRICS_PATH) as f:
        metrics = json.load(f)

    print("=" * 60)
    print("FAKE INTERNSHIP DETECTOR - MODEL EVALUATION REPORT")
    print("=" * 60)
    print(f"Dataset size:        {metrics['dataset_size']}")
    print(f"  Legitimate:        {metrics['legitimate_count']}")
    print(f"  Fraudulent:        {metrics['fraudulent_count']}")
    print(f"Train / Test split:  {metrics['train_size']} / {metrics['test_size']}")
    print(f"TF-IDF features:     {metrics['tfidf_max_features']}")
    print(f"Structured features: {len(metrics['structured_feature_names'])}")
    print()

    print(f"{'Model':<22}{'Accuracy':>10}{'F1(macro)':>12}{'F1(fraud)':>12}"
          f"{'Prec(fraud)':>13}{'Recall(fraud)':>15}")
    print("-" * 84)
    for r in metrics["all_model_reports"]:
        print(f"{r['model']:<22}{r['accuracy']:>10.4f}{r['f1_macro']:>12.4f}"
              f"{r['f1_fraudulent_class']:>12.4f}"
              f"{r['precision_fraudulent_class']:>13.4f}"
              f"{r['recall_fraudulent_class']:>15.4f}")

    print()
    print(f">>> Best model (by F1 on fraudulent class): {metrics['best_model']} <<<")
    print()

    best = next(r for r in metrics["all_model_reports"]
                if r["model"] == metrics["best_model"])
    cm = best["confusion_matrix"]
    print("Confusion matrix (best model), rows=actual, cols=predicted:")
    print("                 Pred: Legit   Pred: Fraud")
    print(f"Actual: Legit    {cm[0][0]:>10}   {cm[0][1]:>10}")
    print(f"Actual: Fraud    {cm[1][0]:>10}   {cm[1][1]:>10}")

    print()
    print(f"Plots saved in {OUTPUTS_DIR}/:")
    for fname in sorted(os.listdir(OUTPUTS_DIR)):
        print(f"  - {fname}")

    print()
    print(f"Total training time (last run): {metrics['training_time_seconds']}s")


if __name__ == "__main__":
    main()
