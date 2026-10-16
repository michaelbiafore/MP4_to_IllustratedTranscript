# Translating a Code-Switched Mandarin Transcript

A field guide to turning a Whisper transcript of a **Mandarin-language working meeting** into
an English formatted transcript. Companion to
[`Chinese_to_English_Figures.md`](Chinese_to_English_Figures.md), which covers the *figures*;
this note covers the *speech*.

Written from `Yuting_Demo_20261015_182534.mp4` (2026-10-15) — a 50-minute buy-side product
demo in Mandarin, delivered to
`Output/Formatted/Building_A_Self_Learning_Research_AI_FORMATTED_TRANSCRIPT.{md,html}`.
1,453 ASR segments, ~3,700 words, two speakers.

---

## 0. Why this is its own problem

A professional Mandarin meeting in a global firm is not Chinese with a few loanwords. It is
**code-switched**: the connective tissue is Mandarin, and most of the terms of art arrive in
English, mid-sentence, in the speaker's own voice:

> 然后我们的架构大概就是 … 比如说像 **earnings review** 或者说 **company historical stock
> movement** 的这个 tracking

So the job is not "translate Chinese to English". It is **fill in English around the English
that is already there**, without flattening the two speakers' very different registers.

---

## 1. Do not reach for Whisper's `--task translate`

Settled, twice over, and worth restating here because it is the first instinct:

- `large-v3-turbo` **has no translation head**. `task=translate` is silently a no-op: you get
  a beautiful, confident transcript in the source language and no warning at all.
- `large-v3` *can* translate, but the 3 GB `model.bin` download has repeatedly failed on this
  machine (HF LFS CDN closing the connection partway).
- Even when it works, Whisper's translation is **lossy in exactly the wrong place**: it
  renders the code-switched English back into generic English and throws away which words the
  speaker actually said in English. That distinction is load-bearing in a transcript.

**Do this instead:** `--language zh --task transcribe` on turbo (fast, fully cached), then
translate by hand while writing the document. The hand translation is better, and it is the
only point at which you can apply §2–§6 below.

---

## 2. Three distinct error classes in a Chinese ASR transcript

They need three different repair strategies. Sort every suspect token into one of them.

### 2a. Garbled English fragments

The speaker said an English term; Whisper heard it through Mandarin phonetics and emitted
something that is *nearly* the word. These are the most common and the easiest to miss,
because they read as plausible nonsense.

| In the transcript | Actually | How you know |
|---|---|---|
| `boomburg` | Bloomberg | on screen in the architecture figure |
| `bitable alpha` | Visible Alpha | on screen |
| `fact sets` | FactSet | on screen |
| `X-watchless` | X Watchlist | the panel's own title bar |
| `Selsa` / `销塞` | sell side | context + 卖方 used elsewhere |
| `obesity 店` / `obesity 点` | Obsidian | the vault is visible in the demo |
| `Dymo MCP`, `Diamond Shandad` | Dymon MCP, Dymon's standard | firm name |
| `PMOPSET` | PM offsite | "I'll be writing this up at the ___ next week" |
| `suanli` | 算力 / compute | Jay says it mid-English-sentence |
| `thumbtion` | assumption | "Ben has his own ___" |
| `a tax spec at a budget` | a tech spec and a budget | the sentence demands it |
| `askb` | ask BBG | listed beside "Claude" |
| `aas 一个新的 analyst` | you hire a new analyst | |
| `雅歌 infrastructure` | `grapeot/context-infrastructure` | the repo name is in the figure |

### 2b. Chinese homophone substitutions

Phonetically right, semantically wrong. The transcript *looks* clean, which is why these are
dangerous — a literal translation produces a confident, wrong sentence.

| In the transcript | Actually | A literal translation would say |
|---|---|---|
| 美食股票 | 每只股票 | "gourmet stocks" |
| 管你曾承诺 | 管理层承诺 | "mind you once promised" |
| 品位 | 品味 (taste, judgement) | "rank / status" |
| 质朴的 5.3 模型 | 智谱 (Zhipu) | "a plain, unadorned 5.3 model" |
| 轮巡 | 轮询 (polling) | "patrol" |
| 你学一身 | earnings (review) | nonsense |

**The tell:** a word that reads oddly in a slot the syntax says must hold a proper noun, a
product, or a term of art. 质朴 appears in a list of model vendors — that is the signal, not
the characters.

### 2c. Names and people

Treat these as the highest-risk class, because a mistake here invents a human being.

- 雨婷 → **Yuting**; 班 → **Ben**; `Benwei` → **Ben Wei** (confirmed by the task feed in the
  AI Desk screenshot and the `JNJ_PM-note_..._Benwei` filename in the vault).
- At 31:42 the transcript says *"看看 **Tim** 有没有什么问题吧"* — but the meeting's own Zoom
  title card reads *"Yuting's demo with Jay, Lan, Sienna"* and only two people are ever on
  camera. **Do not translate a participant into existence.** Render the line neutrally
  ("then let's see if there are any questions") and say so in the intro blockquote.
- Conversely, the title card and the participant strip are *evidence*: they are how the
  questioner was identified as Jay in the first place.

---

## 3. The screen is the dictionary

This is the single highest-leverage technique, and it is specific to screencasts.

The speaker is demonstrating software whose UI, file names, section headings and architecture
diagrams are all on screen at the moment they are speaking. **Resolve every garbled English
token against the frames, not against the audio.** Fourteen of the fifteen fixes in §2a came
straight off a screenshot.

Practical order of work:

1. Extract and curate the frames **first**, before translating a word.
2. Read the authored on-screen documents (an overview deck, a README, a knowledge file) end to
   end. This is careful written Chinese by the same person — far cleaner than their speech,
   and it is where the house terminology is defined.
3. Only then translate the speech, with that vocabulary already fixed.

---

## 4. Never translate line by line

Whisper segments on VAD pauses, not sentences. In this recording the mean segment was ~2.5
words:

```
[1:06] 那这个东西我们现在分为四步
[1:09] 第一步就是先学习
[1:12] 先吸收知识
[1:13] 那就是我们会run一些正常的
```

Translated line by line this yields staccato fragments that read like a bad subtitle track.
**Re-join into speaker turns, then translate the turn as a paragraph**, re-punctuating into
English sentences. Mandarin business speech runs on loosely-chained clauses; English needs
full stops put back in.

While re-joining, also drop:

- **Echo duplicates.** One participant's mic was not muted (they stop to fix it at 4:19), so
  Whisper emitted many adjacent near-identical lines. These are an artifact of the room, not
  repetition by the speaker — deduplicate before translating or you will faithfully render a
  stutter that never happened.
- **Backchannel.** 对 / 嗯 / 好 / 是是是 are acknowledgement tokens. Rendering each one as
  "Right." "Yes." "OK." triples the line count and makes a fluent speaker sound monosyllabic.
  Collapse them, or fold them into the next sentence.

---

## 5. Code-switching policy: keep what they said in English

State the policy in the intro blockquote and apply it without exception:

> The spoken Mandarin has been rendered into English; the English words and product names the
> speakers used are kept as they said them.

Concretely:

- **Keep verbatim:** product and vendor names, file names, metric names, and the English terms
  of art (`initiation`, `preview`, `coverage`, `narrative`, `beat / miss`, `bull / base /
  bear`, `sandbox`, `pod`, `MCP`, `token`). These are the working vocabulary; translating
  `initiation` into "initiating-coverage report" every time is both noisy and *less* accurate.
- **Translate:** everything Mandarin around them.
- **Quote, don't paraphrase:** where a speaker switches wholesale into English — the senior
  participant here did so for every strategic passage — that stretch is already in the target
  language. Reproduce it, lightly cleaned. "Go for the big one", "No one's going to say no to
  that", "just write it as your wish list" are the man's own words and carry his register;
  smoothing them into your own prose loses the thing worth preserving.
- **Signal the fixes, don't hide them.** The intro blockquote lists every correction from §2
  with its original. A reader who knows the domain can then audit you.

---

## 6. One glossary, shared with the figures

If the figures are being reconstructed in English (per `Chinese_to_English_Figures.md`) and
the prose is being translated, they *must* share one glossary — otherwise 知识库 is a
"knowledge base" in Figure 4 and a "knowledge repository" three paragraphs later, and the
document quietly contradicts itself.

**Build the glossary from the figures first.** The authored Chinese in a deck is deliberate;
the speech is improvised. Fix the term from the deck, then make the speech match.

### Working glossary from this recording

*Research process*

| 中文 | English |
|---|---|
| 投研 | investment research |
| 卖方 / 买方 | sell side / buy side |
| 建仓研究 | initiating coverage |
| 财报前瞻 / 复盘 | earnings preview / review (post-mortem) |
| 异动 | unusual price move |
| 一致预期 | consensus |
| 预期差 | expectation gap |
| 驱动因子 | driver / driving factor |
| 数字锚 | number anchors |
| 催化剂日历 | catalyst calendar |
| 分歧 | disagreement, divergence |
| 看多 / 看空 / 中性 | bullish / bearish / neutral |
| 指引 | guidance |
| 口径 | basis, definition (of a number) |
| 归因 / 分层归因 | attribution / layered attribution |
| 超额 | excess return |
| 评级回测 | rating backtest |
| 纪要 / 路演 / 点评 | minutes / roadshow / note |
| 空头占流通盘 | short interest as a share of free float |
| 回补天数 | days to cover |
| 情景区间 / 落入哪个情景 | scenario bands / which scenario it landed in |
| 稀释 EPS / 净收入 / 承销 | diluted EPS / net revenue / underwriting |
| 净新增资产 / 税前利润率 | net new assets / pre-tax margin |
| 专利悬崖 | patent cliff |
| 剔除 | excluding |

*System and process*

| 中文 | English |
|---|---|
| 关系图谱 / 知识图谱 | relationship graph / knowledge graph |
| 个股知识库 | per-stock knowledge base |
| 一手来源 | first-party sources |
| 采集层 / 本地数据层 / 交付层 | collection layer / local data layer / delivery layer |
| 本地面板群 | the local panels |
| 强制机制 | enforcement |
| 安全边界 | security boundary |
| 回写 | write back |
| 闸门 / 门控 | gate |
| 沉淀 | settle into, accumulate into |
| 底座 | base layer, foundation |
| 轮询 | polling sweep |
| 骨架 / 零 token | skeleton / zero-token |
| 烧 token | burn tokens |
| 算力 | compute |
| 品味 | taste, judgement |
| 自进化 / 自学习 | self-evolving / self-learning |

---

## 7. Captions for screenshots that stay in Chinese

When the UI itself is left in Chinese (which it should be — see
[`Chinese_to_English_Figures.md`](Chinese_to_English_Figures.md) §0 on why dense live screens
are evidence, not candidates for reconstruction), the caption carries the whole translation
load. Two rules:

- **Say what it does, in English, with the real numbers.** "Sell-side Topic Dashboard —
  4,591 research emails from 2026-09-10 to 2026-10-15 broken into 9,885 individual views,
  auto-rescanned every 15 minutes" beats "the email dashboard".
- **Don't write the caption as if the UI were English.** Describe the function; quote a
  Chinese label only when the label itself is the point.

Note that pandoc with `-f markdown-implicit_figures` leaves the caption in `alt` text, where
nobody sees it. For a translated document that is a real loss — rewrap the images as
`<figure>/<figcaption>` at build time (`scripts/caption_figures.py` does this).

---

## 8. Numbers are your anchor

Digits, tickers and dates survive Chinese ASR almost perfectly, and they are frequently
visible on screen at the same moment. Use them to verify any passage you are unsure of:
*"antropic Q3 的 tolar revenue 是 168 亿美金"* is garbled around a number that is not —
**$16.8bn** — and that fixes the rest of the sentence.

---

## 9. Checklist

- [ ] Transcribed with `--language zh --task transcribe`; **no** reliance on `--task translate`.
- [ ] Frames extracted and the on-screen authored documents read **before** translating.
- [ ] Every suspect token sorted into garbled-English / homophone / name, and resolved against
      the screen.
- [ ] No participant invented; names cross-checked against the title card or participant list.
- [ ] Echo duplicates and backchannel removed; segments re-joined into speaker turns before
      translating.
- [ ] English the speakers actually spoke kept verbatim; wholesale-English passages quoted,
      not paraphrased.
- [ ] One glossary across figures and prose, derived from the figures.
- [ ] Every correction listed in the intro blockquote, with the original.
- [ ] Screenshot captions carry the English, and are visible in the built HTML.
