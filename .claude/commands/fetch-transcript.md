# Fetch YouTube Transcript

Download a YouTube video transcript and save it to the Input directory.

**YouTube URL**: $ARGUMENTS

## Instructions

1. **Run the fetch script** using uv to ensure the correct environment:
   ```bash
   uv run python scripts/fetch_transcript.py "$ARGUMENTS"
   ```

2. **Report the result**:
   - Confirm the output filename and location
   - Show a preview of the transcript (first 10-15 lines)
   - Remind the user they can run `/format-transcript <filename>` on the new file

## Error Handling

- If the video has no transcript available, report this to the user
- If the URL format is invalid, show examples of valid formats:
  - `https://youtu.be/VIDEO_ID`
  - `https://www.youtube.com/watch?v=VIDEO_ID`
- If pytube fails to get the title, the script will error - suggest trying again or checking the URL

## Example Usage

```
/fetch-transcript https://youtu.be/uVZMc-i5EEs
```

Output will be saved as: `Input/{VideoTitle}_RAW_TRANSCRIPT.md`
