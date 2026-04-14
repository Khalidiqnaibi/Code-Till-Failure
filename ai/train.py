"""
train.py — Road Hazard Classifier Training
============================================
Fine-tunes MobileNetV3-Small (pretrained ImageNet) on your 5-class dataset.

Usage:
  python train.py                                    # defaults
  python train.py --data_dir data --epochs 30
  python train.py --resume checkpoints/last.pt       # continue training
  python train.py --epochs 10 --freeze_backbone      # head-only warm-up
"""

import argparse
import json
import time
from pathlib import Path
from collections import Counter

import torch
import torch.nn as nn
import torchvision.transforms as T
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision.datasets import ImageFolder
import timm

# ── Transforms ────────────────────────────────────────────────────────────────
# Strong augmentation to simulate varied user photo conditions:
# shaky hands, different angles, glare, night/day, close/far

TRAIN_TF = T.Compose([
    T.RandomResizedCrop(224, scale=(0.6, 1.0), ratio=(0.75, 1.33)),
    T.RandomHorizontalFlip(),
    T.RandomVerticalFlip(p=0.05),
    T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.08),
    T.RandomRotation(20),
    T.RandomGrayscale(p=0.05),           # some users share B&W screenshots
    T.RandomPerspective(distortion_scale=0.2, p=0.3),
    T.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    T.RandomErasing(p=0.1, scale=(0.02, 0.1)),   # simulate obstructions/UI overlays
])

VAL_TF = T.Compose([
    T.Resize(256),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


# ── Model ─────────────────────────────────────────────────────────────────────

def build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    """MobileNetV3-Small: ~6 MB, fast on CPU, good accuracy."""
    return timm.create_model(
        "mobilenetv3_small_100",
        pretrained=pretrained,
        num_classes=num_classes,
    )


def freeze_backbone(model: nn.Module):
    """Freeze all layers except the final classifier head."""
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = False


def unfreeze_all(model: nn.Module):
    for param in model.parameters():
        param.requires_grad = True


# ── Balanced sampler ──────────────────────────────────────────────────────────

def make_balanced_sampler(dataset: ImageFolder) -> WeightedRandomSampler:
    """
    Compensate for class imbalance (soldiers class is usually smaller).
    Each class gets equal expected samples per epoch.
    """
    counts = Counter(dataset.targets)
    total = len(dataset)
    class_weights = {cls: total / count for cls, count in counts.items()}
    sample_weights = [class_weights[t] for t in dataset.targets]
    return WeightedRandomSampler(sample_weights, num_samples=total, replacement=True)


# ── Training helpers ──────────────────────────────────────────────────────────

def train_epoch(model, loader, criterion, optimizer, device, scaler=None):
    model.train()
    loss_sum, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        if scaler:                              # AMP (GPU only)
            with torch.autocast(device_type="cuda"):
                logits = model(imgs)
                loss   = criterion(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(imgs)
            loss   = criterion(logits, labels)
            loss.backward()
            optimizer.step()

        loss_sum += loss.item() * imgs.size(0)
        correct  += (logits.argmax(1) == labels).sum().item()
        total    += imgs.size(0)
    return loss_sum / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    loss_sum, correct, total = 0.0, 0, 0
    # Per-class accuracy
    class_correct = {}
    class_total   = {}
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        logits = model(imgs)
        loss   = criterion(logits, labels)
        preds  = logits.argmax(1)
        loss_sum += loss.item() * imgs.size(0)
        correct  += (preds == labels).sum().item()
        total    += imgs.size(0)
        for p, l in zip(preds.cpu().tolist(), labels.cpu().tolist()):
            class_correct[l] = class_correct.get(l, 0) + int(p == l)
            class_total[l]   = class_total.get(l, 0) + 1

    per_class = {k: class_correct.get(k, 0) / class_total[k] for k in class_total}
    return loss_sum / total, correct / total, per_class


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",        default="data")
    parser.add_argument("--epochs",          type=int,   default=25)
    parser.add_argument("--batch_size",      type=int,   default=32)
    parser.add_argument("--lr",              type=float, default=3e-4)
    parser.add_argument("--workers",         type=int,   default=4)
    parser.add_argument("--out_dir",         default="checkpoints")
    parser.add_argument("--resume",          default=None)
    parser.add_argument("--freeze_backbone", action="store_true",
                        help="Freeze backbone — only train head (fast warm-up)")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"
    print(f"Device : {device}  |  AMP : {use_amp}")

    # ── Data ──────────────────────────────────────────────────────────────────
    train_dir = Path(args.data_dir) / "train"
    val_dir   = Path(args.data_dir) / "val"

    if not train_dir.exists():
        raise SystemExit(
            f"\n[ERROR] '{train_dir}' not found.\n"
            "Run first:  python download_data.py\n"
        )

    train_ds = ImageFolder(train_dir, transform=TRAIN_TF)
    val_ds   = ImageFolder(val_dir,   transform=VAL_TF)
    classes  = train_ds.classes
    n_cls    = len(classes)

    print(f"Classes ({n_cls}) : {classes}")
    counts = Counter(train_ds.targets)
    for i, cls in enumerate(classes):
        print(f"  {cls:<20} {counts[i]:>5} train images")
    print(f"Val images       : {len(val_ds)}")

    sampler = make_balanced_sampler(train_ds)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size,
                              sampler=sampler, num_workers=args.workers, pin_memory=True)
    val_loader   = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                              num_workers=args.workers, pin_memory=True)

    # ── Model ─────────────────────────────────────────────────────────────────
    model      = build_model(n_cls).to(device)
    start_ep   = 0
    best_acc   = 0.0

    if args.freeze_backbone:
        freeze_backbone(model)
        print("Backbone frozen — training head only.")

    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model"])
        start_ep = ckpt.get("epoch", 0) + 1
        best_acc = ckpt.get("val_acc", 0.0)
        print(f"Resumed from {args.resume}  (epoch {start_ep}, best_acc {best_acc:.3f})")

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                      lr=args.lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    scaler    = torch.cuda.amp.GradScaler() if use_amp else None

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "classes.json", "w") as f:
        json.dump({str(i): c for i, c in enumerate(classes)}, f, indent=2)

    history = []
    print(f"\n{'Ep':>4} {'TrLoss':>8} {'TrAcc':>7} {'VlLoss':>8} {'VlAcc':>7}  {'s':>5}")
    print("─" * 50)

    for ep in range(start_ep, start_ep + args.epochs):
        t0 = time.time()

        # Unfreeze full model after 3 warm-up epochs if backbone was frozen
        if args.freeze_backbone and ep == start_ep + 3:
            unfreeze_all(model)
            optimizer = AdamW(model.parameters(), lr=args.lr * 0.1, weight_decay=1e-4)
            print("  → Backbone unfrozen, lr reduced ×0.1")

        tr_loss, tr_acc        = train_epoch(model, train_loader, criterion, optimizer, device, scaler)
        vl_loss, vl_acc, pcls  = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        elapsed = time.time() - t0
        flag = " ← best" if vl_acc > best_acc else ""
        print(f"{ep+1:>4} {tr_loss:>8.4f} {tr_acc*100:>6.2f}% {vl_loss:>8.4f} {vl_acc*100:>6.2f}%  {elapsed:>4.0f}s{flag}")

        # Per-class breakdown every 5 epochs
        if (ep + 1) % 5 == 0 or vl_acc > best_acc:
            for i, cls in enumerate(classes):
                acc = pcls.get(i, 0)
                print(f"       {cls:<20} {acc*100:5.1f}%")

        history.append({"epoch": ep+1, "train_loss": tr_loss, "train_acc": tr_acc,
                         "val_loss": vl_loss, "val_acc": vl_acc})

        # Save checkpoints
        ckpt_data = {"model": model.state_dict(), "epoch": ep,
                     "val_acc": vl_acc, "classes": classes}
        if vl_acc > best_acc:
            best_acc = vl_acc
            torch.save(ckpt_data, out_dir / "best.pt")
        torch.save(ckpt_data, out_dir / "last.pt")

    with open("training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nDone. Best val accuracy : {best_acc*100:.2f}%")
    print(f"Checkpoint saved to     : {out_dir}/best.pt")
    print("\nNext → run inference:")
    print("  python predict.py path/to/image.jpg")


if __name__ == "__main__":
    main()