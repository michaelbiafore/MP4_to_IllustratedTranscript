#!/bin/bash

# Find SLIDES HTML files modified on or after 2/12/2026 10:30 AM
OUTPUT_DIR="A:/Packages/Transcript2MDSlides/Output"
CUTOFF_DATE="2026-02-12 10:30:00"

# Find matching files and store in array
mapfile -t files < <(find "$OUTPUT_DIR" -maxdepth 1 -name "*SLIDES*.html" -newermt "$CUTOFF_DATE" 2>/dev/null)

# Display count and file list
echo "Found ${#files[@]} matching file(s):"
for file in "${files[@]}"; do
    filename=$(basename "$file")
    modtime=$(stat -c '%y' "$file" 2>/dev/null || stat -f '%Sm' "$file" 2>/dev/null)
    echo "  $filename  ($modtime)"
done

# Open each file in Chrome
for file in "${files[@]}"; do
    # Windows (Git Bash / WSL)
    if command -v cmd.exe &>/dev/null; then
        cmd.exe /c start chrome "$file"
    # macOS
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        open -a "Google Chrome" "$file"
    # Linux
    else
        google-chrome "$file" &>/dev/null &
    fi
done
