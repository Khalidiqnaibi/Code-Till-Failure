"""
predict.py — Road Hazard Inference
=====================================
Loads a trained checkpoint and classifies road images.

CLI usage:
  python predict.py photo.jpg
  python predict.py photo.jpg --model checkpoints/best.pt
  python predict.py images/              # whole folder
  python predict.py images/ --json       # JSON output

Module usage:
  from predict import RoadHazardClassifier

  clf = RoadHazardClassifier("checkpoints/best.pt")
  result = clf.predict("photo.jpg")

  # result:
  # {
  #   "hazard_detected": True,
  #   "hazard_type": "pothole",       # None when clear
  #   "confidence": 0.94,
  #   "all_scores": {
  #     "pothole": 0.94,
  #     "construction": 0.03,
  #     "busy_traffic": 0.01,
  #     "soldiers": 0.01,
  #     "clear": 0.01
  #   }
  # }
"""

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
import torchvision.transforms as T
from PIL import Image
import timm

IMG_EXTS      = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
HAZARD_LABELS = {"pothole", "construction", "busy_traffic", "soldiers"}

INFER_TF = T.Compose([
    T.Resize(256),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class RoadHazardClassifier:
    def __init__(self, checkpoint: str = "checkpoints/best.pt"):
        ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
        self.classes: list = ckpt["classes"]
        self.model = timm.create_model(
            "mobilenetv3_small_100",
            pretrained=False,
            num_classes=len(self.classes),
        )
        self.model.load_state_dict(ckpt["model"])
        self.model.eval()

    @torch.no_grad()
    def predict(self, image_path: str) -> dict:
        img    = Image.open(image_path).convert("RGB")
        tensor = INFER_TF(img).unsqueeze(0)
        logits = self.model(tensor)
        probs  = F.softmax(logits, dim=1)[0]

        scores    = {cls: round(probs[i].item(), 4) for i, cls in enumerate(self.classes)}
        top_idx   = probs.argmax().item()
        top_class = self.classes[top_idx]
        top_conf  = round(probs[top_idx].item(), 4)
        is_hazard = top_class in HAZARD_LABELS

        return {
            "hazard_detected": is_hazard,
            "hazard_type":     top_class if is_hazard else None,
            "confidence":      top_conf,
            "all_scores":      scores,
        }

    def predict_batch(self, image_paths: list) -> list:
        return [self.predict(p) for p in image_paths]


# ── Pretty printer ─────────────────────────────────────────────────────────────

ICONS = {
    "pothole":      "⚠ ",
    "construction": "🚧",
    "busy_traffic": "🚗",
    "soldiers":     "⛔",
    "clear":        "✓ ",
}

def _pretty(filename: str, result: dict):
    icon = ICONS.get(result["hazard_type"] or "clear", "?")
    label = result["hazard_type"].upper() if result["hazard_detected"] else "CLEAR"
    print(f"{'─'*52}")
    print(f"  File       : {filename}")
    print(f"  Result     : {icon}  {label}")
    print(f"  Confidence : {result['confidence']*100:.1f}%")
    print(f"  Scores:")
    for cls, sc in sorted(result["all_scores"].items(), key=lambda x: -x[1]):
        bar = "█" * int(sc * 32)
        print(f"    {cls:<18} {sc*100:5.1f}%  {bar}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Road hazard classifier — inference")
    parser.add_argument("input",   help="Image file or folder")
    parser.add_argument("--model", default="checkpoints/best.pt")
    parser.add_argument("--json",  action="store_true", help="Print JSON output")
    args = parser.parse_args()

    if not Path(args.model).exists():
        sys.exit(
            f"[ERROR] Checkpoint not found: {args.model}\n"
            "Train first:  python train.py --data_dir data"
        )

    print(f"Loading model from {args.model} …", file=sys.stderr)
    clf = RoadHazardClassifier(args.model)
    print(f"Classes: {clf.classes}", file=sys.stderr)

    inp = Path(args.input)

    if inp.is_file():
        result = clf.predict(str(inp))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            _pretty(inp.name, result)

    elif inp.is_dir():
        images = sorted(p for p in inp.iterdir() if p.suffix.lower() in IMG_EXTS)
        if not images:
            sys.exit(f"No images found in '{inp}'.")
        all_results = {}
        for img in images:
            try:
                r = clf.predict(str(img))
                all_results[img.name] = r
                if not args.json:
                    _pretty(img.name, r)
            except Exception as e:
                print(f"[SKIP] {img.name}: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps(all_results, indent=2))
    else:
        sys.exit(f"[ERROR] Not found: {inp}")


if __name__ == "__main__":
    main()