"""Train Sequence-Pair Classifier for Rubric Grading (RoBERTa / Baselines).

Supports:
- Fine-tuning RoBERTa-large (or base) on sequence pairs (criterion, proposition) -> 4-way label.
- Majority class and TF-IDF + Logistic Regression baselines.
- --smoke flag for fast CPU testing without GPU or heavy downloads.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np

LABEL_LIST = ["FULL_CREDIT", "PARTIAL_CREDIT", "MISCONCEPTION", "NO_CREDIT"]
LABEL2ID = {lbl: i for i, lbl in enumerate(LABEL_LIST)}
ID2LABEL = {i: lbl for i, lbl in enumerate(LABEL_LIST)}


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def load_dataset(data_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    train_data = data.get("train", [])
    val_data = data.get("validation", [])
    return train_data, val_data


def compute_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    acc = accuracy_score(y_true, y_pred)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    return {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(f1_macro), 4),
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "weighted_f1": round(float(f1_weight), 4),
    }


def run_baselines(train_data: List[Dict[str, Any]], val_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Majority Class and TF-IDF + Logistic Regression baselines."""
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    y_train = [LABEL2ID[item["label"]] for item in train_data]
    y_val = [LABEL2ID[item["label"]] for item in val_data]

    # Baseline 1: Majority Class
    majority_label = Counter(y_train).most_common(1)[0][0]
    maj_pred = [majority_label] * len(y_val)
    maj_metrics = compute_metrics(y_val, maj_pred)
    maj_metrics["majority_label"] = ID2LABEL[majority_label]

    # Baseline 2: TF-IDF + Logistic Regression
    X_train_text = [f"{item['criterion']} </s> {item['response']}" for item in train_data]
    X_val_text = [f"{item['criterion']} </s> {item['response']}" for item in val_data]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_val_vec = vectorizer.transform(X_val_text)

    clf = LogisticRegression(class_weight="balanced", max_iter=200, random_state=42)
    clf.fit(X_train_vec, y_train)
    lr_pred = clf.predict(X_val_vec)
    lr_metrics = compute_metrics(y_val, lr_pred)

    return {
        "majority_baseline": maj_metrics,
        "tfidf_logreg_baseline": lr_metrics,
    }


def run_smoke_training(args: argparse.Namespace) -> Dict[str, Any]:
    """Lightweight smoke mode to verify training pipeline on CPU in under 5 seconds."""
    print("=== Running Smoke Training Mode (CPU) ===")
    train_data, val_data = load_dataset(args.data_path)
    print(f"Loaded {len(train_data)} train samples, {len(val_data)} validation samples.")

    # Run baselines
    baselines = run_baselines(train_data, val_data)
    print("Baselines computed:")
    print("  Majority Class:", baselines["majority_baseline"])
    print("  TF-IDF + LogReg:", baselines["tfidf_logreg_baseline"])

    # Save mock artifacts into output_dir
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "label_map.json"), "w", encoding="utf-8") as f:
        json.dump({"id2label": ID2LABEL, "label2id": LABEL2ID}, f, indent=2)

    smoke_results = {
        "mode": "smoke",
        "model_name": args.model_name,
        "baselines": baselines,
        "eval_metrics": baselines["tfidf_logreg_baseline"],
        "status": "COMPLETED",
    }
    with open(os.path.join(args.output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(smoke_results, f, indent=2)

    print(f"Smoke training complete. Artifacts saved to {args.output_dir}")
    return smoke_results


def run_torch_training(args: argparse.Namespace) -> Dict[str, Any]:
    """Full PyTorch / HuggingFace Transformers fine-tuning loop."""
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        get_linear_schedule_with_warmup,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device} | Model: {args.model_name}")

    train_data, val_data = load_dataset(args.data_path)
    baselines = run_baselines(train_data, val_data)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    ).to(device)

    class TextPairDataset(Dataset):
        def __init__(self, data: List[Dict[str, Any]]):
            self.data = data

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            item = self.data[idx]
            enc = tokenizer(
                item["criterion"],
                item["response"],
                truncation=True,
                max_length=args.max_length,
                padding="max_length",
                return_tensors="pt",
            )
            item_out = {k: v.squeeze(0) for k, v in enc.items()}
            item_out["labels"] = torch.tensor(LABEL2ID[item["label"]], dtype=torch.long)
            return item_out

    train_dataset = TextPairDataset(train_data)
    val_dataset = TextPairDataset(val_data)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps,
    )

    best_val_f1 = -1.0
    best_metrics = {}
    os.makedirs(args.output_dir, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        # Validation
        model.eval()
        val_preds: List[int] = []
        val_targets: List[int] = []
        with torch.no_grad():
            for batch in val_loader:
                labels = batch["labels"].tolist()
                batch = {k: v.to(device) for k, v in batch.items()}
                logits = model(**batch).logits
                preds = torch.argmax(logits, dim=-1).cpu().tolist()
                val_preds.extend(preds)
                val_targets.extend(labels)

        metrics = compute_metrics(val_targets, val_preds)
        print(f"Epoch {epoch}/{args.epochs} - Loss: {total_loss/len(train_loader):.4f} - Val Macro-F1: {metrics['macro_f1']}")

        if metrics["macro_f1"] > best_val_f1:
            best_val_f1 = metrics["macro_f1"]
            best_metrics = metrics
            model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)

    with open(os.path.join(args.output_dir, "label_map.json"), "w", encoding="utf-8") as f:
        json.dump({"id2label": ID2LABEL, "label2id": LABEL2ID}, f, indent=2)

    results = {
        "model_name": args.model_name,
        "best_val_metrics": best_metrics,
        "baselines": baselines,
    }
    with open(os.path.join(args.output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="AutoRubric Classifier Fine-Tuner")
    parser.add_argument("--model_name", type=str, default="roberta-base", help="Model name or HuggingFace path")
    parser.add_argument("--data_path", type=str, default=str(Path(__file__).parent / "data" / "sample_dataset.json"))
    parser.add_argument("--output_dir", type=str, default=str(Path(__file__).parent / "checkpoint"))
    parser.add_argument("--max_length", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke", action="store_true", help="Run CPU smoke mode without heavy model downloads")

    args = parser.parse_args()
    set_seed(args.seed)

    if args.smoke:
        run_smoke_training(args)
    else:
        run_torch_training(args)


if __name__ == "__main__":
    main()
