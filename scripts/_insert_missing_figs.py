"""Insert missing figures into the BBG OH-01 formatted transcript."""
import re

FIG_BASE = "../../Input/BBG_OH_01_20260520_200105_figs_filtered/"

# Missing figures: num -> (filename, short_caption)
MISSING = {
    31: ("frame_007m40s_screen_031.jpg", "Excalidraw whiteboard — neural network diagram with multiple layers, weights matrix annotations."),
    32: ("frame_007m50s_screen_032.jpg", "Excalidraw whiteboard — neural network layer diagram, Ashwin annotating weight connections between neurons."),
    36: ("frame_009m30s_screen_036.jpg", "Excalidraw whiteboard — linear layer with non-linearity block; y = f(Wx + b) formulation visible."),
    37: ("frame_010m50s_screen_037.jpg", "Excalidraw whiteboard — neural network layers diagram with activations highlighted; backpropagation flow annotated."),
    38: ("frame_011m00s_screen_038.jpg", "Excalidraw whiteboard — three-layer neural network showing activation values flowing forward through the network."),
    39: ("frame_011m20s_screen_039.jpg", "Excalidraw whiteboard — weights update illustration; loss function label visible."),
    40: ("frame_011m40s_screen_040.jpg", "Excalidraw whiteboard — backpropagation and optimizer update path highlighted."),
    41: ("frame_012m00s_screen_041.jpg", "Excalidraw whiteboard — neural network building block with activation functions labeled."),
    42: ("frame_012m10s_screen_042.jpg", "Excalidraw whiteboard — same neural network view, Ashwin pointing to specific weight connections."),
    43: ("frame_012m50s_screen_043.jpg", "ChatGPT — Ashwin showing a response about activation functions (ReLU, SiLU)."),
    44: ("frame_013m10s_screen_044.jpg", "ChatGPT — response listing common non-linearities: ReLU (max(0, x)), sigmoid, tanh, SiLU formulas."),
    45: ("frame_013m30s_screen_045.jpg", "ChatGPT — continuation of activation function explanation."),
    46: ("frame_013m40s_screen_046.jpg", "ChatGPT — ReLU formula and interpretation: if negative set to 0, else keep x."),
    47: ("frame_014m00s_screen_047.jpg", "ChatGPT — non-linearity discussion showing advanced activations used in frontier LLMs (SwiGLU, SiLU)."),
    48: ("frame_014m10s_screen_048.jpg", "ChatGPT — activation function comparisons used across GPT-2, GPT-3, and newer models."),
    49: ("frame_015m10s_screen_049.jpg", "ByteByteAI community portal — course announcements; Ashwin returning to navigation after ChatGPT demo."),
    50: ("frame_015m40s_screen_050.jpg", "ByteByteAI community — course content navigation, Week 1 section."),
    51: ("frame_015m50s_screen_051.jpg", "ByteByteAI community — Week 1 Q&A page or guided learning section."),
    52: ("frame_016m10s_screen_052.jpg", "ByteByteAI community — Ashwin responding to Twisha Desai about structuring Week 1 study; foundations vs. applications framing."),
    53: ("frame_016m50s_screen_053.jpg", "ByteByteAI community — additional resources / links section visible."),
    54: ("frame_017m00s_screen_054.jpg", "ByteByteAI community — Vimal Sudhakar's decoder-only transformer question begins."),
    55: ("frame_017m10s_screen_055.jpg", "ByteByteAI community — course page with transformer architecture section link visible."),
    56: ("frame_017m20s_screen_056.jpg", "ByteByteAI community — course navigation showing Week 1 material on transformers."),
    57: ("frame_017m40s_screen_057.jpg", "ByteByteAI community — Ashwin navigating to the transformer section of the course canvas."),
    58: ("frame_017m50s_screen_058.jpg", "ByteByteAI community — course portal, Ashwin about to switch to Excalidraw for transformer architecture."),
    59: ("frame_018m00s_screen_059.jpg", "Excalidraw whiteboard — beginning to show transformer architecture diagram from the course canvas."),
    61: ("frame_019m20s_screen_061.jpg", "Excalidraw whiteboard — neural network sequence-of-layers diagram (left) with Transformer architecture diagram (right, section 2.3), showing encoder and decoder stacks."),
    62: ("frame_019m30s_screen_062.jpg", "Excalidraw whiteboard — transformer architecture view; chat panel shows participants confirming audio."),
    63: ("frame_021m30s_screen_063.jpg", "Excalidraw whiteboard — Transformer architecture (section 2.3), full encoder-decoder structure. Ashwin explaining encoder vs. decoder stacks for text generation."),
    65: ("frame_022m50s_screen_065.jpg", "Excalidraw whiteboard — section 2.4 decoder-only transformer beginning to appear on the canvas."),
    66: ("frame_023m00s_screen_066.jpg", "Excalidraw whiteboard — decoder-only transformer section (2.4), simplified decoder stack used for text generation."),
    67: ("frame_023m20s_screen_067.jpg", "Excalidraw whiteboard — comparison view: full encoder-decoder (left) vs. decoder-only (right)."),
    68: ("frame_023m30s_screen_068.jpg", "Excalidraw whiteboard — decoder-only transformer diagram with causal attention mask highlighted."),
    69: ("frame_023m40s_screen_069.jpg", "Excalidraw whiteboard — decoder-only transformer, token-by-token generation illustrated."),
    70: ("frame_025m40s_screen_070.jpg", "Excalidraw whiteboard — tokenization section (section 2.2) of the course canvas. Tokenizer diagram showing token IDs."),
    71: ("frame_025m50s_screen_071.jpg", "Excalidraw whiteboard — tokenization diagram showing vocabulary lookup and token ID mapping."),
    72: ("frame_026m20s_screen_072.jpg", "Excalidraw whiteboard — tokenization: word-to-ID mapping and ID-to-word reverse mapping (encode/decode dictionaries)."),
    73: ("frame_026m50s_screen_073.jpg", "Excalidraw whiteboard — tokenization section with three components: vocabulary list, word-to-ID map, ID-to-word map."),
    74: ("frame_027m00s_screen_074.jpg", "Excalidraw whiteboard — tokenizer three-component diagram; these three structures constitute the complete tokenizer."),
    75: ("frame_027m20s_screen_075.jpg", "Excalidraw whiteboard — tokenization and project template link. Saturday deep-dive labs mentioned."),
    76: ("frame_029m30s_screen_076.jpg", "Excalidraw whiteboard — top-K and top-P sampling section; probability distribution diagram visible."),
    77: ("frame_029m40s_screen_077.jpg", "Excalidraw whiteboard — top-K/top-P sampling diagram showing token probability distribution and cutoff threshold."),
    78: ("frame_029m50s_screen_078.jpg", "Excalidraw whiteboard — generation sampling diagram; cumulative probability (top-P) threshold illustrated."),
    79: ("frame_030m30s_screen_079.jpg", "Excalidraw whiteboard — text generation section showing token-by-token sampling loop."),
    80: ("frame_032m50s_screen_080.jpg", "Excalidraw whiteboard — encoder-decoder transformer architecture comparison. Ashwin navigating for Vikram R's decoder-only vs. encoder-decoder question."),
    81: ("frame_033m00s_screen_081.jpg", "Excalidraw whiteboard — transformer architecture overview, encoder stack and decoder stack side by side."),
    82: ("frame_034m40s_screen_082.jpg", "Excalidraw whiteboard — transformer architecture diagram; Ashwin discussing why decoder-only models dominate text generation."),
    83: ("frame_034m50s_screen_083.jpg", "Excalidraw whiteboard — decoder-only architecture diagram. Google search for '3+3=' visible in address bar (LLM math example)."),
    84: ("frame_035m00s_screen_084.jpg", "Browser — Google search results for a math query, illustrating Ashwin's point about LLMs and statistical pattern matching vs. actual arithmetic."),
    85: ("frame_035m10s_screen_085.jpg", "Browser — Google or LLM interface showing a factual query result. Ashwin explaining how training data frequency makes factually common answers more probable."),
    86: ("frame_035m20s_screen_086.jpg", "Browser — search or LLM output showing answer to a simple math/factual query, illustrating statistical vs. reasoning behavior."),
    87: ("frame_036m00s_screen_087.jpg", "Browser — news article or blog post: an OpenAI model solving a previously unsolved mathematical problem. Ashwin referencing a new frontier model result."),
    88: ("frame_036m10s_screen_088.jpg", "Browser — OpenAI research article showing frontier model solving a novel problem."),
    89: ("frame_036m20s_screen_089.jpg", "Browser — OpenAI paper or blog post, key findings about novel AI discovery."),
    90: ("frame_036m30s_screen_090.jpg", "Browser — OpenAI research page continued."),
    91: ("frame_036m40s_screen_091.jpg", "Browser — research paper on novel AI capabilities, Ashwin noting the TLDR."),
    92: ("frame_036m50s_screen_092.jpg", "Browser — paper about frontier model discoveries, Ashwin acknowledging it is hard to follow technically."),
    93: ("frame_037m10s_screen_093.jpg", "Zoom — back to Zoom participant view; Vikram R's tile shown as Ashwin tries to give him the floor."),
    94: ("frame_037m20s_screen_094.jpg", "Zoom — Vikram R audio troubleshooting; chat shows 'Vikram R: Let me check my audio'."),
    95: ("frame_037m30s_screen_095.jpg", "Zoom — audio check continues, other participants waiting."),
    96: ("frame_037m40s_screen_096.jpg", "Zoom — Vikram R unable to unmute; Ashwin moving to next participant (Sarath Medasani)."),
    97: ("frame_038m00s_screen_097.jpg", "Zoom — Sarath Medasani begins subword tokenization question. Chat panel shows Vikram R's typed questions about benchmarks and SFT vs. RL."),
    98: ("frame_038m30s_screen_098.jpg", "Zoom / course canvas — Ashwin navigating to tokenization section to answer Sarath's typo/token-cost question."),
    99: ("frame_038m40s_screen_099.jpg", "Excalidraw whiteboard — tokenization section visible; BPE algorithm diagram."),
    100: ("frame_039m20s_screen_100.jpg", "ChatGPT — Ashwin opening ChatGPT to demonstrate the image generation prompt enhancement example."),
    101: ("frame_039m40s_screen_101.jpg", "ChatGPT — prompt 'generate an image of a dog' entered; ChatGPT routing to DALL-E with an enhanced caption."),
    102: ("frame_039m50s_screen_102.jpg", "ChatGPT — image generation result showing a dog image, illustrating prompt enhancement in practice."),
    103: ("frame_040m20s_screen_103.jpg", "ChatGPT / browser — prompt enhancement example continued; simple user input expanded to detailed caption."),
    104: ("frame_040m30s_screen_104.jpg", "ChatGPT — detailed DALL-E caption generated from simple user prompt."),
    105: ("frame_040m40s_screen_105.jpg", "Browser — typo handling example; Ashwin typing 'attentionn' in Google Search to show how search handles misspellings."),
    106: ("frame_040m50s_screen_106.jpg", "Google Search — 'attentionn' query handled; results for 'attention' returned despite typo, illustrating typo tolerance."),
    113: ("frame_043m10s_screen_113.jpg", "Browser — STaR paper search result; Ashwin navigating to the bootstrapping reasoning paper."),
    114: ("frame_043m30s_screen_114.jpg", "arxiv.org — STaR paper detail page, abstract visible."),
    115: ("frame_043m50s_screen_115.jpg", "arxiv.org — STaR paper, methodology section showing self-taught reasoning pipeline diagram."),
    116: ("frame_044m20s_screen_116.jpg", "Browser — search for 'star paper bootstrapping' in Google, autocomplete suggestions visible."),
    120: ("frame_045m30s_screen_120.jpg", "arxiv.org — STaR paper, showing the iterative self-improvement loop: generate rationale then filter correct then train then repeat."),
    121: ("frame_045m40s_screen_121.jpg", "arxiv.org — STaR paper, experimental results section."),
    130: ("frame_050m40s_screen_130.jpg", "arxiv.org — DeepSeek-R1 paper, RL scaling section showing how more compute during RL phase improves model quality."),
    131: ("frame_051m10s_screen_131.jpg", "arxiv.org — DeepSeek-R1 paper, section comparing RL vs. SFT. Ashwin explaining the scaling advantage of RL in verifiable domains."),
    132: ("frame_051m30s_screen_132.jpg", "arxiv.org — DeepSeek-R1 paper, showing math and coding benchmark results from RL-only training (DeepSeek-R1-Zero)."),
    147: ("frame_062m40s_screen_147.jpg", "Browser — LLM answer to 'I want to wash my car. The car wash is 50 meters away. Should I walk or drive?' showing the model incorrectly recommending walking."),
    148: ("frame_062m50s_screen_148.jpg", "Browser — LLM car-wash answer continued; Ashwin noting frontier models with trillions of parameters get this wrong."),
    149: ("frame_063m40s_screen_149.jpg", "Browser — follow-up LLM comparison test for the car-wash question across different models."),
    150: ("frame_063m50s_screen_150.jpg", "Browser — car-wash question results across multiple LLMs showing the same common-sense failure."),
    151: ("frame_064m00s_screen_151.jpg", "Browser — Ashwin navigating away from car-wash example, transitioning to the embedding question."),
    152: ("frame_064m20s_screen_152.jpg", "Excalidraw whiteboard — navigating to the embedding section of the course canvas."),
    153: ("frame_064m30s_screen_153.jpg", "Excalidraw whiteboard — embedding section of the course canvas; token IDs to embedding lookup table to vectors flow diagram."),
    154: ("frame_065m20s_screen_154.jpg", "Excalidraw whiteboard — RAG section partially visible; Ashwin explaining how embedding models are used in retrieval."),
    155: ("frame_065m30s_screen_155.jpg", "Excalidraw whiteboard — embedding model concept: inputs mapped to high-dimensional vector space; semantically similar inputs land nearby."),
    156: ("frame_065m40s_screen_156.jpg", "Excalidraw whiteboard — embedding model vs. embedding layer distinction illustrated side by side on the course canvas."),
}

def make_fig_line(num, fname, caption):
    return f"![Figure {num}: {caption}]({FIG_BASE}{fname})"

with open("Output/Formatted/bbg-office-hour-01_FORMATTED_TRANSCRIPT.md", "r", encoding="utf-8") as f:
    content = f.read()

# Insert each missing figure after the last figure that precedes it in numeric order
# We build an ordered list and insert after the closest preceding figure

# For each missing fig, find its nearest lower-numbered figure in the content
# and insert after the end of that figure's image line

def insert_after_figure(content, after_num, new_figs_text):
    """Insert new_figs_text immediately after the image line for figure after_num."""
    pattern = rf"(!\[Figure {after_num}:.*?\]\([^)]+\))"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        end = match.end()
        content = content[:end] + "\n\n" + new_figs_text + content[end:]
        return content, True
    return content, False

# Group missing figures by their closest preceding present figure
# Present figures (from the doc):
present = sorted([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
                  33,34,35,60,64,107,108,109,110,111,112,117,118,119,122,123,124,125,126,127,128,129,
                  133,134,135,136,137,138,139,140,141,142,143,144,145,146,157,158,159,160,161,162,163,
                  164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,
                  185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200,201,202,203,204,205,
                  206,207,208,209,210])

missing_sorted = sorted(MISSING.keys())

# Group consecutive missing figs that share the same preceding anchor
from collections import defaultdict
groups = defaultdict(list)
for m in missing_sorted:
    # find largest present number < m
    anchor = max([p for p in present if p < m], default=None)
    if anchor:
        groups[anchor].append(m)

# Process groups in reverse order of anchor to avoid offset issues
for anchor in sorted(groups.keys(), reverse=True):
    figs = sorted(groups[anchor])
    block = "\n\n".join(make_fig_line(n, MISSING[n][0], MISSING[n][1]) for n in figs)
    content, ok = insert_after_figure(content, anchor, block)
    if ok:
        print(f"  Inserted figs {figs} after fig {anchor}")
    else:
        print(f"  WARNING: could not find fig {anchor} to insert after")

with open("Output/Formatted/bbg-office-hour-01_FORMATTED_TRANSCRIPT.md", "w", encoding="utf-8") as f:
    f.write(content)

# Count final figures
count = content.count("![Figure ")
print(f"\nFinal figure count: {count}")
