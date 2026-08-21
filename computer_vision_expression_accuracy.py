"""Computer vision expression recognition evaluation utilities.

This module focuses on real-world accuracy for facial expression recognition (FER):
- evaluate on a held-out test split, not on training data
- use subject-independent splits when possible
- report overall accuracy and macro-F1
- print a confusion matrix for class-level inspection

It intentionally avoids relying on a single training accuracy metric because that
can be misleading on imbalanced expression datasets.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Sequence, Tuple


def compute_accuracy(labels: Sequence[int], predictions: Sequence[int]) -> float:
    """Return accuracy = correct / total."""
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have the same length")
    if not labels:
        return 0.0

    correct = sum(int(gt == pred) for gt, pred in zip(labels, predictions))
    return correct / float(len(labels))


def compute_confusion_matrix(
    labels: Sequence[int],
    predictions: Sequence[int],
    num_classes: int,
) -> List[List[int]]:
    """Build a confusion matrix of shape [num_classes, num_classes]."""
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have the same length")
    if num_classes <= 0:
        raise ValueError("num_classes must be positive")

    matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for gt, pred in zip(labels, predictions):
        if gt < 0 or gt >= num_classes:
            raise ValueError(f"Label {gt} is outside [0, {num_classes})")
        if pred < 0 or pred >= num_classes:
            raise ValueError(f"Prediction {pred} is outside [0, {num_classes})")
        matrix[gt][pred] += 1
    return matrix


def compute_macro_f1(labels: Sequence[int], predictions: Sequence[int], num_classes: int) -> float:
    """Compute macro-F1 for multiclass classification.

    F1 for each class = 2 * precision * recall / (precision + recall)
    Macro-F1 averages the per-class F1 values equally.
    """
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have the same length")
    if num_classes <= 0:
        raise ValueError("num_classes must be positive")

    confusion = compute_confusion_matrix(labels, predictions, num_classes)
    per_class_f1 = []
    for class_id in range(num_classes):
        tp = confusion[class_id][class_id]
        fp = sum(confusion[i][class_id] for i in range(num_classes)) - tp
        fn = sum(confusion[class_id][j] for j in range(num_classes)) - tp

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class_f1.append(f1)

    return sum(per_class_f1) / float(num_classes)


def format_confusion_matrix(matrix: Sequence[Sequence[int]]) -> str:
    """Pretty print a confusion matrix for console output."""
    if not matrix or not matrix[0]:
        return "[]"

    width = max(len(str(value)) for row in matrix for value in row)
    rows = []
    for row in matrix:
        rows.append("  " + "  ".join(f"{value:>{width}}" for value in row))
    return "\n".join(rows)


def evaluate_model(model, dataloader, device, num_classes: int, class_names: Sequence[str] | None = None):
    """Run evaluation on a PyTorch-style dataloader.

    Parameters
    ----------
    model:
        A PyTorch nn.Module.
    dataloader:
        Iterable over (images, labels).
    device:
        e.g. torch.device("cuda") or torch.device("cpu")
    num_classes:
        Number of expression classes.
    class_names:
        Optional labels for reporting, e.g. ['angry', 'happy', ...].

    Returns
    -------
    dict
        Example:
        {
            "accuracy": 0.83,
            "macro_f1": 0.81,
            "confusion_matrix": [[...], [...]],
            "per_class_accuracy": {...},
            "class_names": [...],
        }
    """
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError("PyTorch is required to run evaluate_model().") from exc

    model.eval()
    predictions: List[int] = []
    labels: List[int] = []

    with torch.no_grad():
        for images, batch_labels in dataloader:
            images = images.to(device)
            batch_labels = batch_labels.to(device)
            logits = model(images)
            preds = torch.argmax(logits, dim=1)

            predictions.extend(preds.detach().cpu().tolist())
            labels.extend(batch_labels.detach().cpu().tolist())

    accuracy = compute_accuracy(labels, predictions)
    macro_f1 = compute_macro_f1(labels, predictions, num_classes)
    confusion_matrix = compute_confusion_matrix(labels, predictions, num_classes)

    per_class_accuracy = {}
    for class_id in range(num_classes):
        class_indices = [idx for idx, label in enumerate(labels) if label == class_id]
        if not class_indices:
            per_class_accuracy[class_id] = 0.0
            continue
        class_correct = sum(1 for idx in class_indices if predictions[idx] == class_id)
        per_class_accuracy[class_id] = class_correct / float(len(class_indices))

    if class_names is not None:
        class_name_map = {idx: class_names[idx] for idx in range(min(num_classes, len(class_names)))}
    else:
        class_name_map = {idx: str(idx) for idx in range(num_classes)}

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "confusion_matrix": confusion_matrix,
        "per_class_accuracy": {class_name_map[k]: v for k, v in per_class_accuracy.items()},
        "class_names": [class_name_map.get(i, str(i)) for i in range(num_classes)],
    }


def build_subject_independent_split(subject_ids: Sequence[str], test_subjects: Sequence[str], val_subjects: Sequence[str]):
    """Return train/val/test indices using fixed subjects for each split.

    This is the preferred setup for FER because it avoids leakage from the same
    subject appearing in both train and test sets.
    """
    subject_to_indices = defaultdict(list)
    for idx, subject in enumerate(subject_ids):
        subject_to_indices[str(subject)].append(idx)

    train_indices = []
    for subject, idxs in subject_to_indices.items():
        if subject not in set(test_subjects) and subject not in set(val_subjects):
            train_indices.extend(idxs)

    val_indices = []
    for subject in val_subjects:
        val_indices.extend(subject_to_indices.get(str(subject), []))

    test_indices = []
    for subject in test_subjects:
        test_indices.extend(subject_to_indices.get(str(subject), []))

    return train_indices, val_indices, test_indices


def evaluate_real_accuracy(
    labels: Sequence[int],
    predictions: Sequence[int],
    num_classes: int,
    class_names: Sequence[str] | None = None,
) -> dict:
    """Compute the main metrics for a real FER evaluation run.

    This is the practical implementation of the earlier recommendation: use a
    held-out test split and report accuracy, macro-F1, and confusion matrix.
    """
    accuracy = compute_accuracy(labels, predictions)
    macro_f1 = compute_macro_f1(labels, predictions, num_classes)
    confusion = compute_confusion_matrix(labels, predictions, num_classes)

    report = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "confusion_matrix": confusion,
    }

    if class_names is not None:
        report["class_names"] = list(class_names)

    return report


if __name__ == "__main__":
    # Example: emotion classes 0..3 with a synthetic held-out test set.
    example_labels = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
    example_predictions = [0, 1, 2, 3, 1, 1, 3, 3, 0, 0, 2, 3]

    result = evaluate_real_accuracy(
        labels=example_labels,
        predictions=example_predictions,
        num_classes=4,
        class_names=["angry", "happy", "neutral", "surprised"],
    )

    print("Real accuracy report")
    print(f"Accuracy: {result['accuracy']:.4f}")
    print(f"Macro-F1: {result['macro_f1']:.4f}")
    print("Confusion matrix:")
    print(format_confusion_matrix(result["confusion_matrix"]))
