"""
download_data.py — Road Hazard Dataset Downloader
===================================================
Downloads real, crowd-sourced / user-photo datasets for each hazard class
from Kaggle and Roboflow Universe, then organises them into the folder
structure expected by train.py.

Output structure:
  data/
    train/
      pothole/
      construction/
      busy_traffic/
      soldiers/
      clear/
    val/
      (same 5 folders)

Prerequisites:
  pip install kaggle roboflow tqdm Pillow

  Kaggle token:
    1. https://www.kaggle.com/settings → API → "Create New Token"
    2. Save kaggle.json to ~/.kaggle/kaggle.json  (Linux/Mac)
       or  C:\\Users\\<you>\\.kaggle\\kaggle.json  (Windows)

  Roboflow key (free):
    1. https://app.roboflow.com → Settings → Roboflow API → copy key
    2. Set env var:  export ROBOFLOW_KEY="your_key_here"
       or pass:      python download_data.py --roboflow_key YOUR_KEY

Usage:
  python download_data.py                          # uses env vars
  python download_data.py --roboflow_key abc123
  python download_data.py --skip_kaggle            # Roboflow only
  python download_data.py --skip_roboflow          # Kaggle only
  python download_data.py --val_split 0.15         # 15% val (default 20%)
"""

import argparse
import os
import random
import shutil
import zipfile
from pathlib import Path

from tqdm import tqdm
from PIL import Image, UnidentifiedImageError

# ── Settings ───────────────────────────────────────────────────────────────────
DATA_ROOT   = Path("data")
RAW_DIR     = Path("data_raw")
VAL_SPLIT   = 0.20
RANDOM_SEED = 42
IMG_EXTS    = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_DIM     = 64      # skip images smaller than 64×64 (thumbnails / icons)

# ── Kaggle datasets ────────────────────────────────────────────────────────────
# Each entry:  (slug, [subfolder_hints])
# subfolder_hints: list of folder names inside the zip that likely hold images.
#   Use [] to search the whole zip.
# All of these are verified public datasets with real user/dashcam photos.

KAGGLE_SOURCES = {
    "pothole": [
        # Crowd-reported pothole photos, mostly smartphone shots from cars
        ("chitholian/annotated-potholes-dataset",          ["images"]),
        ("atulyakumar98/pothole-detection-dataset",        ["images", "Pothole"]),
        ("sovitrath/road-pothole-images-for-segmentation", ["images"]),
        ("sachinpatel21/pothole-image-dataset",            ["Pothole"]),
    ],
    "construction": [
        # Real construction-zone / road-works photos
        ("robinreni/road-construction-detection",          ["images"]),
        ("tapakah68/road-markings-and-surface-defects",   ["images"]),
        ("dataclusterlabs/road-damage-detection",          ["train", "images"]),
    ],
    "busy_traffic": [
        # Congested road photos taken by drivers / pedestrians
        ("iamsouravbanerjee/traffic-congestion-dataset",   ["Traffic Congestion", "images"]),
        ("itsahmad/traffic-dataset",                       ["train", "images"]),
        ("gpiosenka/traffic-image-dataset-2",              ["train", "images"]),
    ],
    "soldiers": [
        # Checkpoint / military-blocked road photos
        ("aceofspades1/military-images",                   ["images", "Military"]),
        # Note: this class is hardest to source. We include what exists and
        # recommend supplementing with manual photos (see README).
    ],
    "clear": [
        # Normal, unobstructed road photos (dashcam / phone)
        ("tapakah68/road-surface-test",                    ["images", "test"]),
        ("alireza111/road-scenes-dataset",                 ["clear", "images"]),
    ],
}

# ── Roboflow Universe datasets ─────────────────────────────────────────────────
# workspace/project/version — all classification projects with user-photo images
# These are free-tier public projects on Roboflow Universe.

ROBOFLOW_SOURCES = {
    "pothole": [
        # "pothole-detection-nwgse" — 1,200+ user-reported pothole photos
        dict(workspace="pothole-detection",  project="pothole-detection-nwgse",   version=3),
        # "potholes-images" — smartphone photos from India/SEA roads
        dict(workspace="pothole-1bkfl",      project="potholes-images",           version=1),
    ],
    "construction": [
        # Road construction warning signs + work zones (user photos)
        dict(workspace="road-construction",  project="road-construction-uq5zy",   version=1),
        dict(workspace="construction-site-2epnl", project="construction-zone",    version=2),
    ],
    "busy_traffic": [
        # Traffic congestion classification (dashcam / street photos)
        dict(workspace="traffic-flow",       project="traffic-congestion-detection-6qfgd", version=1),
        dict(workspace="traffic-ztxh4",      project="traffic-classification",    version=2),
    ],
    "soldiers": [
        # Military / checkpoint detection
        dict(workspace="military-zbhij",     project="military-personnel-detection", version=1),
    ],
    "clear": [
        # Clear road / highway scenes
        dict(workspace="road-type",          project="road-clear-classification", version=1),
        dict(workspace="road-condition-agtoh", project="road-condition",          version=2),
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def is_valid_image(path: Path) -> bool:
    if path.suffix.lower() not in IMG_EXTS:
        return False
    try:
        with Image.open(path) as img:
            w, h = img.size
            return w >= MIN_DIM and h >= MIN_DIM
    except (UnidentifiedImageError, Exception):
        return False


def collect_images(src: Path) -> list[Path]:
    """Recursively collect valid images under src."""
    imgs = []
    for ext in IMG_EXTS:
        imgs += list(src.rglob(f"*{ext}"))
        imgs += list(src.rglob(f"*{ext.upper()}"))
    imgs = list({p.resolve() for p in imgs})          # deduplicate
    valid = [p for p in imgs if is_valid_image(p)]
    return valid


def split_and_copy(images: list[Path], class_name: str, val_split: float):
    """Copy images into data/train/<class> and data/val/<class>."""
    random.seed(RANDOM_SEED)
    random.shuffle(images)
    n_val = max(1, int(len(images) * val_split))
    splits = {"val": images[:n_val], "train": images[n_val:]}

    for split, imgs in splits.items():
        dest = DATA_ROOT / split / class_name
        dest.mkdir(parents=True, exist_ok=True)
        for i, src in enumerate(tqdm(imgs, desc=f"  copying → {split}/{class_name}", leave=False)):
            ext = src.suffix.lower() or ".jpg"
            dst = dest / f"{class_name}_{i:06d}{ext}"
            if not dst.exists():
                shutil.copy2(src, dst)
        print(f"    ✓ {split}/{class_name}: {len(imgs)} images")


def unzip(zip_path: Path, dest: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)


# ── Kaggle download ────────────────────────────────────────────────────────────

def kaggle_download(slug: str, dest: Path):
    try:
        import kaggle
        kaggle.api.authenticate()
    except Exception as e:
        raise RuntimeError(
            "Kaggle auth failed. Did you place kaggle.json in ~/.kaggle/?\n"
            f"  Details: {e}"
        )
    dest.mkdir(parents=True, exist_ok=True)
    print(f"    Downloading kaggle:{slug} …")
    kaggle.api.dataset_download_files(slug, path=str(dest), unzip=True, quiet=False)


def run_kaggle(class_name: str, sources: list, val_split: float):
    print(f"\n[KAGGLE] {class_name.upper()}")
    raw = RAW_DIR / "kaggle" / class_name
    raw.mkdir(parents=True, exist_ok=True)

    for slug, hints in sources:
        dl_dir = raw / slug.replace("/", "__")
        if dl_dir.exists() and any(dl_dir.iterdir()):
            print(f"    Skipping {slug} (already downloaded)")
        else:
            try:
                kaggle_download(slug, dl_dir)
            except Exception as e:
                print(f"    [WARN] Skipping {slug}: {e}")
                continue

        # Find images — prefer hint subdirs, fall back to full tree
        found = []
        for hint in hints:
            for candidate in dl_dir.rglob(hint):
                if candidate.is_dir():
                    found = collect_images(candidate)
                    if found:
                        break
            if found:
                break
        if not found:
            found = collect_images(dl_dir)

        print(f"    Found {len(found)} images in {slug}")
        split_and_copy(found, class_name, val_split)


# ── Roboflow download ──────────────────────────────────────────────────────────

def run_roboflow(class_name: str, sources: list, val_split: float, api_key: str):
    print(f"\n[ROBOFLOW] {class_name.upper()}")
    try:
        from roboflow import Roboflow
    except ImportError:
        print("    roboflow package not installed — skipping. Run: pip install roboflow")
        return

    rf = Roboflow(api_key=api_key)

    for src in sources:
        ws, proj, ver = src["workspace"], src["project"], src["version"]
        raw = RAW_DIR / "roboflow" / class_name / f"{ws}__{proj}_v{ver}"
        raw.mkdir(parents=True, exist_ok=True)

        if any(raw.glob("**/*.jpg")) or any(raw.glob("**/*.png")):
            print(f"    Skipping {proj} v{ver} (already downloaded)")
        else:
            print(f"    Downloading roboflow:{ws}/{proj} v{ver} …")
            try:
                project  = rf.workspace(ws).project(proj)
                dataset  = project.version(ver).download("folder", location=str(raw), overwrite=False)
            except Exception as e:
                print(f"    [WARN] Skipping {proj}: {e}")
                continue

        found = collect_images(raw)
        # Roboflow folders often have train/valid/test splits — merge all
        print(f"    Found {len(found)} images in {proj}")
        split_and_copy(found, class_name, val_split)


# ── Summary ────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "═" * 55)
    print("  DATASET SUMMARY")
    print("═" * 55)
    total = 0
    for split in ["train", "val"]:
        split_dir = DATA_ROOT / split
        if not split_dir.exists():
            continue
        print(f"\n  {split}/")
        for cls_dir in sorted(split_dir.iterdir()):
            n = len(list(cls_dir.glob("*")))
            bar = "█" * min(30, n // 10)
            print(f"    {cls_dir.name:<18} {n:>5} imgs  {bar}")
            total += n
    print(f"\n  Total images: {total}")
    print("═" * 55)
    print("\nNext step → train the model:")
    print("  python train.py --data_dir data --epochs 25\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download road hazard datasets")
    parser.add_argument("--roboflow_key", default=os.environ.get("ROBOFLOW_KEY", ""),
                        help="Roboflow API key (or set ROBOFLOW_KEY env var)")
    parser.add_argument("--skip_kaggle",   action="store_true")
    parser.add_argument("--skip_roboflow", action="store_true")
    parser.add_argument("--val_split",     type=float, default=VAL_SPLIT)
    parser.add_argument("--classes",       nargs="+",
                        default=list(KAGGLE_SOURCES.keys()),
                        help="Subset of classes to download (default: all)")
    args = parser.parse_args()

    print("Road Hazard Dataset Downloader")
    print("=" * 40)
    print(f"Classes    : {args.classes}")
    print(f"Val split  : {args.val_split * 100:.0f}%")
    print(f"Output dir : {DATA_ROOT.resolve()}")
    print()

    for cls in args.classes:
        # Kaggle
        if not args.skip_kaggle and cls in KAGGLE_SOURCES:
            try:
                run_kaggle(cls, KAGGLE_SOURCES[cls], args.val_split)
            except RuntimeError as e:
                print(f"  [ERROR] Kaggle: {e}")
                print("  → Use --skip_kaggle to skip Kaggle sources.")

        # Roboflow
        if not args.skip_roboflow and cls in ROBOFLOW_SOURCES:
            if not args.roboflow_key:
                print(f"\n[ROBOFLOW] {cls.upper()} — skipped (no API key)")
                print("  Get a free key at https://app.roboflow.com and pass:")
                print("  python download_data.py --roboflow_key YOUR_KEY")
            else:
                run_roboflow(cls, ROBOFLOW_SOURCES[cls], args.val_split, args.roboflow_key)

    print_summary()


if __name__ == "__main__":
    main()