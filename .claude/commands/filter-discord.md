# Filter Discord Channel by Context

Fetch a Discord channel and return only messages relevant to a user-supplied context query, ranked by relevance.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<channel_id> "<context>" [--top M] [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--token <token>]`

- **channel_id** (required): Discord channel ID (numeric string)
- **context** (required): Free-text context query in quotes describing what to filter for. Supports Boolean operators `<AND>`, `<OR>`, `<NOT>` to compose conditions. These are literal tokens — not ordinary English words.
- **--top** (optional): Maximum number of postings to return, ranked by relevance. Default: `7`.
- **--after** (optional): Only include messages after this date (YYYY-MM-DD). Default: beginning of channel.
- **--before** (optional): Only include messages before this date (YYYY-MM-DD). Default: now.
- **--token** (optional): Discord authorization token. Default: read from `cookies_discord.txt`.

### Boolean Operators

The context query supports three Boolean operators, written in angle brackets to distinguish from ordinary English:

| Operator | Meaning | Example |
|----------|---------|---------|
| `<AND>` | Both conditions must be relevant | `"hardware <AND> power reliability"` |
| `<OR>` | Either condition is sufficient | `"MLflow errors <OR> bootstrap issues"` |
| `<NOT>` | Exclude messages matching this | `"hardware recommendations <NOT> cloud hosting"` |

Operators can be combined: `"IBKR <AND> Docker <NOT> Windows"`

When no operators are present, treat the entire string as a single context query.

### Evaluation rules for Boolean operators

For each message, evaluate relevance to each sub-query independently, then combine:

- **`A <AND> B`**: Message must be relevant to BOTH A and B. Score = min(score_A, score_B).
- **`A <OR> B`**: Message may be relevant to either. Score = max(score_A, score_B).
- **`<NOT> X`**: If the message is ONLY about X and nothing else relevant, score = 0. If it touches X but also covers relevant content, keep it but reduce score by 30%.
- **Operator precedence**: `<NOT>` binds tightest, then `<AND>`, then `<OR>`. Evaluate left to right within same precedence.

### Examples

```
/filter-discord 1473401675510452285 "MLflow bootstrap errors and solutions"
/filter-discord 1473401675510452285 "hardware recommendations" --top 10 --after 2026-02-19 --before 2026-03-15
/filter-discord 1473401675510452285 "IBKR <AND> Docker <NOT> Windows" --top 5
/filter-discord 1473401675510452285 "FMP API data bandwidth <OR> data limits"
```

## Instructions

### Phase 1: Fetch messages

1. **Run the fetch script**:
   ```bash
   uv run python scripts/fetch_discord.py "<channel_id>" [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--token TOKEN]
   ```
   Pass `--after` and `--before` only if the user specified them.

2. **Parse the script output** to extract:
   - `CHANNEL_NAME`, `SERVER_NAME`, `SLUG`
   - `TOTAL_MESSAGES`, `OUTPUT_PATH`, `DATE_RANGE`

3. **Read the raw JSON** from `OUTPUT_PATH`.

### Phase 2: Parse Boolean context query

4. **Split the context string** on `<AND>`, `<OR>`, `<NOT>` operators. Record which operator connects each pair. If no operators, the entire string is a single query term.

   Example: `"IBKR <AND> Docker <NOT> Windows"` →
   - Terms: `["IBKR", "Docker", "Windows"]`
   - Operators: `[<AND>, <NOT>]`

### Phase 3: Score and rank messages

5. **Read messages in batches of 50.** For each message, evaluate:

   a. **Extract the message text** (content + embed titles/descriptions). Skip messages that are empty or reactions-only.

   b. **Score relevance 0–100** against each sub-query term:
      - **90–100**: Directly answers, solves, or provides key information about the query term
      - **70–89**: Discusses the topic substantially, asks a relevant question, or shares a relevant resource/link
      - **50–69**: Mentions the topic in passing, or is a reply to a highly relevant message
      - **30–49**: Tangentially related — same general domain but not directly about the query
      - **0–29**: Not relevant — greetings, off-topic, unrelated announcements

   c. **Combine sub-query scores** using the Boolean operators (AND → min, OR → max, NOT → suppress/reduce as defined above). This produces a single **combined score** per message.

   d. **Context-adjacent boost**: If a message is a direct reply (within 2 minutes, same conversation thread) to a message scoring 70+, boost its score by +15 (capped at 100). This captures "thanks, that fixed it" and "I had the same issue" follow-ups.

   e. **Image bonus**: If the message has image attachments and the text scores 50+, add +5 to the score. Screenshots of errors, dashboards, and configs are especially valuable in technical contexts.

6. **Collect all scored messages** into a list of `(message, combined_score)` pairs. Discard any with combined_score < 30.

7. **Sort by combined_score descending**. Take the top M messages (default 7).

### Phase 4: Download relevant images

8. **For each of the top M messages**, download any image attachments:
   - Create directory `Input/{slug}_filter_figs/`
   - Download images sequentially: `filter_fig_001.png`, `filter_fig_002.jpg`, etc.
   - Build a mapping of attachment_id → local filename
   - Sleep 0.2s between downloads

### Phase 5: Produce output

9. **Write the filtered output** to `Input/{slug}_FILTERED_{context_slug}.md`:

   Derive `context_slug` from the context query: lowercase, spaces to hyphens, strip punctuation and operators, truncate to 40 chars.

```markdown
# {Channel Name} — Filtered Results

**Server:** {server_name}
**Channel:** #{channel_name}
**Context query:** {context}
**Date range scanned:** {first_date} to {last_date}
**Messages scanned:** {total_count}
**Messages returned:** {M} (of {above_threshold_count} scoring 30+)

---

## Summary

{Write a 2-3 paragraph synthesis of what the top M messages reveal about the context query. Identify the key findings, who contributed them, and any consensus or disagreements. This is the most valuable part — the user may read only this section.}

---

## Top {M} Results (by relevance)

### 1. Score: {score}/100 — {Author} ({date})

{Full message content, with @mentions resolved}

{If image attachments exist:}
![Filter Figure N: filename]({slug}_filter_figs/filter_fig_NNN.ext)

{If embeds exist, include as blockquotes}

---

### 2. Score: {score}/100 — {Author} ({date})

{message content}

---

{...repeat for all M results...}

---

## Key Findings

| # | Finding | Author | Date | Score |
|---|---------|--------|------|-------|
| 1 | {key fact} | {author} | {date} | {score} |
| 2 | {key fact} | {author} | {date} | {score} |
{...}
```

### Phase 6: Report

10. **Report to the user:**
    - Output file path
    - How many messages were scanned and how many scored above threshold
    - The top 3 findings in brief
    - Suggest: "Read the full filtered output or ask follow-up questions about specific findings"

## Error Handling

- If the token is invalid (401): instruct the user to re-extract from browser DevTools
- If the channel ID is invalid (404): show format examples
- If rate limited (429): the fetch script handles this automatically
- If no messages match the context (all scores < 30): report "No relevant messages found for this context query" and suggest broadening the query or adjusting the date range
- If fewer than M messages score 30+, return all that do (don't pad with irrelevant content)
- If image download fails: continue with remaining images, note which failed

## Example Usage

```
/filter-discord 1473401675510452285 "MLflow bootstrap errors and solutions"
/filter-discord 1473401675510452285 "hardware <AND> budget under $2000" --top 10
/filter-discord 1473401675510452285 "UPS <OR> power failure <OR> generator" --after 2026-03-01
/filter-discord 1473401675510452285 "Docker setup <NOT> Windows" --top 5
```
