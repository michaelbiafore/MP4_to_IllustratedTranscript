import os, shutil, json
from PIL import Image

figs = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_03_hires_20260604_195833_figs"
out = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_03_hires_20260604_195833_figs_filtered"
manifest_path = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_03_hires_20260604_195833_frames_manifest.json"
os.makedirs(out, exist_ok=True)

INTERVAL = 10
# (original frame index, short caption tag)
picks = [
    (91,  "voice-to-text demo: Codex CLI session beside an automations doc, with the Whisper Flow dictation app active in the menu bar"),
    (358, "Claude Code /voice and /memory: voice mode (hold Space to record) and the auto-memory panel listing the three memory locations"),
    (359, "Auto-memory turned on; Finder opens the auto-memory folder via 'Open auto-memory folder'"),
    (374, "/agents Library: user, plugin, and built-in agents each with a per-agent model (haiku / sonnet / inherit)"),
    (376, "ai-lane agent detail showing the editable Model field ('Inherit from parent (default)'), tools, and system prompt"),
    (428, "Andrej Karpathy's LLM Wiki GitHub Gist - a markdown pattern for building a persistent, compounding personal knowledge base"),
    (431, "CodeGraph repo: semantic code intelligence for Claude Code / Codex / Cursor, ~58% fewer tool calls, 100% local"),
]

manifest = []
for i, (idx, cap) in enumerate(picks, start=1):
    src = os.path.join(figs, f"frame_{idx:04d}.jpg")
    sec = (idx - 1) * INTERVAL
    mins, secs = sec // 60, sec % 60
    name = f"frame_{mins:03d}m{secs:02d}s_screen_{i:03d}.jpg"
    dst = os.path.join(out, name)
    # re-save as PNG-quality JPEG (keep readable text)
    Image.open(src).save(dst, quality=92)
    manifest.append({
        "figure_num": i,
        "filename": name,
        "timestamp": f"{mins}:{secs:02d}",
        "total_seconds": sec,
        "original_frame": f"frame_{idx:04d}.jpg",
        "caption_hint": cap,
    })
    print(f"{name}  <- frame_{idx:04d}.jpg  ({mins}:{secs:02d})")

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(f"\nManifest: {manifest_path}  ({len(manifest)} figures)")
