#!/usr/bin/env python3
"""Drop selected figures and renumber the survivors sequentially.

Reads the frames manifest, removes the user's drop list (moves files to a
_dropped/ sidecar), renumbers the keepers fig_01.., and rewrites the manifest.

Usage:
  prune_and_renumber_figs.py <figs_dir> <manifest_path> --drop "1,2,7,11,13,19,22,28,29,30,35,36"
"""
import sys, json, shutil, argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("figs_dir")
    ap.add_argument("manifest_path")
    ap.add_argument("--drop", required=True, help="Comma-separated 1-based fig numbers to drop")
    args = ap.parse_args()

    figs_dir = Path(args.figs_dir)
    manifest_path = Path(args.manifest_path)

    drop_set = {int(x.strip()) for x in args.drop.split(",") if x.strip()}
    print(f"Dropping figs: {sorted(drop_set)}", flush=True)

    dropped_dir = figs_dir.parent / (figs_dir.name + "_dropped")
    dropped_dir.mkdir(exist_ok=True)

    # 1) Move dropped figs to sidecar
    for n in sorted(drop_set):
        src = figs_dir / f"fig_{n:02d}.jpg"
        if src.exists():
            shutil.move(str(src), str(dropped_dir / src.name))
            print(f"  moved {src.name} -> {dropped_dir.name}/", flush=True)

    # 2) Renumber survivors
    surviving = sorted(figs_dir.glob("fig_*.jpg"),
                       key=lambda p: int(p.stem.split("_")[1]))
    rename_map = {}  # old_name -> new_name
    for new_idx, src in enumerate(surviving, start=1):
        new_name = f"fig_{new_idx:02d}.jpg"
        if src.name == new_name:
            rename_map[src.name] = new_name
            continue
        # First move to a temporary unique name to avoid collisions, then rename
        tmp = src.with_name(f"_tmp_{new_idx:03d}.jpg")
        src.rename(tmp)
        rename_map[src.name] = new_name
        # Track temp -> final (do final pass after all temp moves)
    # Final pass: rename _tmp_NNN.jpg -> fig_NN.jpg
    tmp_files = sorted(figs_dir.glob("_tmp_*.jpg"),
                       key=lambda p: int(p.stem.split("_")[2]))
    for new_idx, tmp in enumerate(tmp_files, start=1):
        final = figs_dir / f"fig_{new_idx:02d}.jpg"
        tmp.rename(final)

    # Re-list final order
    final = sorted(figs_dir.glob("fig_*.jpg"),
                   key=lambda p: int(p.stem.split("_")[1]))
    print(f"Survivors after renumber: {len(final)}", flush=True)

    # 3) Update manifest: drop old fig_filenames in drop_set, renumber survivors in original order
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    new_idx = 0
    for tgt in manifest["targets"]:
        new_clusters = []
        for c in tgt.get("clusters", []):
            old_fn = c.get("fig_filename", "")
            old_n = int(old_fn.replace("fig_", "").replace(".jpg", ""))
            if old_n in drop_set:
                continue
            new_idx += 1
            c["fig_filename"] = f"fig_{new_idx:02d}.jpg"
            c["original_fig_filename"] = old_fn
            new_clusters.append(c)
        tgt["clusters"] = new_clusters
    manifest["pruned_drops"] = sorted(drop_set)
    manifest["dropped_dir"] = str(dropped_dir)
    manifest["surviving_count"] = new_idx

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    print(f"Updated manifest: {manifest_path}  surviving={new_idx}", flush=True)


if __name__ == "__main__":
    main()
