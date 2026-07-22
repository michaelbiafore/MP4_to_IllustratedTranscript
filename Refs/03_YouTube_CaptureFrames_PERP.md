<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# How to modify ClaudeCode slash command to output timestamps for topic changes

Modify the slash command so it returns a **structured list of topic-change timestamps** instead of only a prose summary. In Claude Code, custom slash commands are just Markdown prompt files, and they can accept arguments via `$ARGUMENTS` or positional placeholders like `$1`, so your command can take the YouTube URL plus options like a minimum topic size or capture offset.[^1][^2][^3]

## Recommended shape

Have the command do three things:

1. Read or fetch the transcript.
2. Detect topic boundaries from the transcript text and timestamps.
3. Output a machine-friendly list, for example JSON or a markdown table, with each topic change timestamp and a suggested capture timestamp a bit earlier.

That gives you an output your downstream script can consume directly, instead of having to parse free-form text.[^4][^3]

## Prompt template

A slash command file like `.claude/commands/topic-shifts.md` can be written to instruct Claude to emit strict structured output. A practical template is:

```md
Analyze the transcript for topic changes.

Input: $ARGUMENTS

Return ONLY JSON with this schema:
{
  "video_url": "...",
  "topics": [
    {
      "topic": "...",
      "start_time": "HH:MM:SS.mmm",
      "capture_time": "HH:MM:SS.mmm",
      "confidence": 0.0
    }
  ]
}

Rules:
- Detect semantic topic changes, not every speaker turn.
- Capture_time should usually be 0.5 to 2.0 seconds before start_time.
- Do not include prose outside the JSON.
```

That format is easy to post-process in a shell script, Python script, or another Claude Code step.[^5][^3][^1]

## Better output format

If you want the command to feed directly into frame extraction, I’d make the output include:

- `start_time`: the transcript boundary.
- `capture_time`: the frame timestamp you will actually extract.
- `topic`: short label for the new topic.
- `confidence`: optional score so you can ignore weak boundaries.

Example output:

```json
{
  "video_url": "https://youtube.com/watch?v=...",
  "topics": [
    {
      "topic": "model architecture",
      "start_time": "00:12:34.500",
      "capture_time": "00:12:33.500",
      "confidence": 0.91
    }
  ]
}
```

That makes the next step trivial: hand `capture_time` to FFmpeg.[^6][^7]

## Implementation pattern

A good architecture is:

- Slash command detects topic boundaries from transcript.
- It emits JSON to stdout or a file.
- A wrapper script reads the JSON.
- The wrapper calls FFmpeg once per `capture_time`.

This is cleaner than making the slash command itself try to do frame extraction, because slash commands are best at orchestration and structured reasoning, while FFmpeg handles the media work.[^8][^3][^6]

## Practical refinement

If your current command already produces transcript segments, just add a second pass that merges adjacent segments into topic blocks, then emits the first timestamp of each block. For capture purposes, subtract a small offset from the boundary, for example `capture_time = start_time - 1.0s`, and clamp at zero if needed.[^7][^9]

A strong default is: keep the topic boundary timestamp, but output a separate capture timestamp that is slightly earlier. That gives you both semantic alignment and a visually safer frame target.[^10][^11]
<span style="display:none">[^12][^13][^14][^15][^16][^17][^18][^19][^20]</span>

<div align="center">⁂</div>

[^1]: https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent

[^2]: https://www.producttalk.org/how-to-use-claude-code-features/

[^3]: https://platform.claude.com/docs/en/agent-sdk/slash-commands

[^4]: https://github.com/jftuga/transcript-critic

[^5]: https://cloudartisan.com/posts/2025-04-14-claude-code-tips-slash-commands/

[^6]: https://ottverse.com/extract-frames-using-ffmpeg-a-comprehensive-guide/

[^7]: https://fftrac-bg.ffmpeg.org/wiki/Seeking

[^8]: https://code.claude.com/docs/en/slash-commands

[^9]: https://gotranscript.com/en/blog/fix-timestamps-timecodes-auto-generated-transcripts

[^10]: https://a.osmarks.net/content/superuser.com_en_all_2020-04/A/question/1044569.html

[^11]: https://stackoverflow.com/questions/33746719/ffmpeg-how-can-i-capture-the-timestamp-of-a-screenshot-using-a-seek-and-findin\&rut=c999cde8d37bd1e8dc472627e664a92692aef6d131740ab4a45de8d6bf5cad74

[^12]: https://timdietrich.me/blog/claude-code-commands-guide/

[^13]: https://www.reddit.com/r/ClaudeAI/comments/1m7fnov/why_does_claude_completely_lose_the_plot_between/

[^14]: https://www.reddit.com/r/ClaudeCode/comments/1r55uy9/i_made_a_plugin_so_claude_code_always_knows_the/

[^15]: https://www.youtube.com/watch?v=3geTTnWD0jc

[^16]: https://m.academy/lessons/create-custom-slash-command-claude-code/

[^17]: https://kentgigger.com/posts/claude-code-conversation-history

[^18]: https://codesignal.com/learn/courses/customizing-claude-code-for-reusable-visualization-workflows/lessons/creating-custom-slash-commands

[^19]: https://github.com/anthropics/claude-code/issues/18582

[^20]: https://rewire.it/blog/the-self-writing-blog-using-claude-code-slash-commands-to-create-content/

