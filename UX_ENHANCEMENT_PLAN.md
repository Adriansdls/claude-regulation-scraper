# Network Science Agent - UX Enhancement Plan

**Goal:** Create the most delightful terminal-based research assistant experience possible.

## Research Sources
- Claude Code architecture (from previous research)
- Modern TUI libraries (Textual, Rich, InquirerPy)
- Terminal plotting libraries (plotext, asciichartpy)
- Best practices from tools like: litecli, pgcli, httpie, gh CLI

---

## TIER 1: High Impact, Immediate (Implement First)

### 1. Multi-line Input with Visual Feedback
**Inspiration:** Claude Code, vim multi-line mode
**Current:** Single line only
**Enhancement:**
- Press `Ctrl+J` or `\` to enter multi-line mode
- Visual indicator showing multi-line mode active
- Syntax highlighting for complex queries
- Line numbers in multi-line mode
- Submit with `Ctrl+D` or empty line

**Impact:** 🔥🔥🔥 Essential for complex queries
**Effort:** Medium (prompt_toolkit supports this)

```python
# Example
You: \
... Find papers that:
... 1. Are about transformers
... 2. Published after 2020
... 3. Have high betweenness
... [Ctrl+D to submit]
```

---

### 2. Smart Autocomplete
**Inspiration:** gh CLI, litecli
**Current:** No autocomplete
**Enhancement:**
- Command autocomplete (help, stats, memory, clear, export, etc.)
- Common query patterns
- Tool names when typing "use X"
- Graph entity names (paper titles, authors, concepts)
- Fuzzy matching
- Context-aware suggestions

**Impact:** 🔥🔥🔥 Huge discoverability and speed boost
**Effort:** Medium (InquirerPy or prompt_toolkit completer)

```python
# Example
You: find gap[TAB]
     → "find gaps in the literature"
     → "find gaps about transformers"
     → "find gaps by algorithm"
```

---

### 3. Terminal Plots & Visualizations
**Inspiration:** asciichartpy, plotext
**Current:** Text-only output
**Enhancement:**
- Plot centrality distributions (histograms)
- Timeline charts (papers over time)
- Network degree distribution
- Community size bar charts
- Citation patterns (line plots)
- Scatter plots for correlations
- ASCII network diagrams (small graphs)

**Impact:** 🔥🔥🔥 "A picture is worth 1000 words"
**Effort:** Low-Medium (plotext is simple)

```
Papers by Year
120┤                                    ╭╮
100┤                                  ╭╯╰╮
 80┤                            ╭─────╯  ╰
 60┤                      ╭─────╯
 40┤          ╭───────────╯
 20┤  ╭───────╯
  0┼──┴──────────────────────────────────
  2015    2017    2019    2021    2023
```

**Impact:** Visualizing metrics makes patterns obvious

---

### 4. Token Usage & Cost Tracking
**Inspiration:** Claude Code token display
**Current:** No visibility
**Enhancement:**
- Real-time token counter in status bar
- Cost estimation ($ per query, $ session total)
- Model info (which Claude model)
- Response time tracking
- Cache hit stats (prompt caching)
- Usage summary on exit

**Impact:** 🔥🔥 Transparency and cost control
**Effort:** Low (tiktoken library)

```
╭─ Status ────────────────────────────────────╮
│ Model: claude-sonnet-4 | Session: $0.42    │
│ Tokens: 23.5K | This query: 3.2K | 1.2s    │
╰─────────────────────────────────────────────╯
```

---

### 5. Progressive Disclosure
**Inspiration:** Modern UIs, email clients
**Current:** All or nothing output
**Enhancement:**
- Show summaries first
- Expandable sections for details
- "Show more..." links
- Collapsible tool results
- Focus on insights, hide raw data

**Impact:** 🔥🔥 Reduced cognitive load
**Effort:** Low (Rich supports this)

```
Agent: I found 8 research communities.

Top 3 by size:
  1. Deep Learning (45 papers) - [dim]show details[/dim]
  2. NLP (32 papers) - [dim]show details[/dim]
  3. Computer Vision (28 papers) - [dim]show details[/dim]

[dim]show all 8 communities[/dim]
```

---

### 6. Session Export
**Inspiration:** ChatGPT export, Claude web
**Current:** No export
**Enhancement:**
- Export conversation to Markdown
- Export insights to JSON
- Export visualizations to text files
- Include timestamps, queries, results
- Auto-save every N queries
- Resume previous sessions

**Impact:** 🔥🔥 Research persistence
**Effort:** Low

```
Commands:
  export markdown session_2024_11_06.md
  export json insights.json
  load session_2024_11_05.json
```

---

### 7. Status Bar / Context Display
**Inspiration:** vim status line, tmux
**Current:** No persistent context
**Enhancement:**
- Top/bottom status bar always visible
- Show: current graph, # papers, # queries, time, cost
- Active tools indicator
- Conversation depth
- Memory usage (# saved insights)

**Impact:** 🔥🔥 Constant context awareness
**Effort:** Medium (Rich Live display)

```
╭─────────────────────────────────────────────────────────╮
│ Graph: ml_papers.json | 423 papers | Query #7 | $0.42  │
╰─────────────────────────────────────────────────────────╯
```

---

### 8. Enhanced Syntax Highlighting
**Inspiration:** Claude Code
**Current:** Basic Rich markdown
**Enhancement:**
- Python code blocks with Pygments
- JSON with syntax highlighting
- NetworkX code highlighting
- Query syntax highlighting
- Error messages with colors
- Inline code highlighting

**Impact:** 🔥 Readability
**Effort:** Low (Pygments)

```python
# Agent shows code with beautiful highlighting
result = nx.pagerank(kg.paper_graph, alpha=0.85)
top_papers = sorted(result.items(), key=lambda x: x[1], reverse=True)[:10]
```

---

## TIER 2: High Value, Medium Effort

### 9. Query Templates & Suggestions
**Current:** User has to know what to ask
**Enhancement:**
- Pre-built query templates
- Fill-in-the-blank queries
- Smart suggestions based on graph
- "You might want to..." recommendations
- Quick actions menu

```
Quick Queries:
  1. Find the 10 most influential papers
  2. Detect communities
  3. Find literature gaps
  4. Show research trends over time
  5. Custom query...

Enter number or type your own:
```

**Impact:** 🔥🔥 Discoverability
**Effort:** Medium

---

### 10. Interactive Graph Navigation (TUI)
**Inspiration:** k9s, lazygit, htop
**Enhancement:**
- Full-screen interactive mode
- Navigate papers like a file explorer
- Expand/collapse communities
- Jump to related papers
- Visual network traversal
- Keyboard navigation (j/k, arrows)

**Implementation:** Textual framework
**Impact:** 🔥🔥🔥 Game-changing exploration
**Effort:** High (full TUI app)

```
╭─ Papers ─────────────────────╮  ╭─ Details ───────────────╮
│ ▾ Deep Learning (45)         │  │ Title: Attention Is All │
│   ▸ Transformers (23)        │  │ You Need                │
│   ▸ CNNs (15)                │  │ Year: 2017              │
│   ▸ RNNs (7)                 │  │ Citations: 45,234       │
│ ▾ NLP (32)                   │  │ PageRank: 0.042         │
│   ▸ LLMs (18)                │  │                         │
│   ▸ Embeddings (14)          │  │ [Press Enter to expand] │
╰──────────────────────────────╯  ╰─────────────────────────╯
```

---

### 11. Bookmarks & Favorites
**Enhancement:**
- Bookmark interesting queries
- Star important papers/insights
- Quick access to favorites
- Tags and collections

```
Commands:
  bookmark "Find transformers papers"
  star paper_id_123
  bookmarks list
  bookmarks run 1
```

**Impact:** 🔥 Workflow efficiency
**Effort:** Low

---

### 12. Performance Profiling
**Enhancement:**
- Show query execution time breakdown
- Tool performance metrics
- Graph algorithm timing
- LLM vs local execution time
- Optimization suggestions

```
Query Performance:
  Total: 2.34s
  ├─ LLM reasoning: 1.2s (51%)
  ├─ detect_communities: 0.8s (34%)
  ├─ calculate_centrality: 0.3s (13%)
  └─ formatting: 0.04s (2%)
```

**Impact:** 🔥 Transparency
**Effort:** Low

---

### 13. Themes & Customization
**Enhancement:**
- Light/dark themes
- Color scheme presets (solarized, dracula, nord)
- Custom color configuration
- Accessibility options (high contrast)
- Font size adjustment

```
Commands:
  theme dark
  theme light
  theme solarized
  theme custom ~/.rge/theme.json
```

**Impact:** 🔥 Personalization
**Effort:** Low (Rich supports themes)

---

## TIER 3: Nice to Have

### 14. Tutorial Mode / Guided Tour
**Enhancement:**
- First-time user walkthrough
- Interactive tutorial
- Example queries with explanations
- Tips and tricks
- Progressive feature introduction

**Impact:** 🔥 Onboarding
**Effort:** Medium

---

### 15. Comparison Mode
**Enhancement:**
- Load multiple knowledge graphs
- Compare side-by-side
- Diff insights
- Track changes over time
- Before/after analysis

**Impact:** 🔥 Advanced use case
**Effort:** High

---

### 16. Collaborative Features
**Enhancement:**
- Share insights (gist-like)
- Export shareable links
- Team memory (shared insights)
- Annotation system

**Impact:** 🔥 Team research
**Effort:** Very High

---

## Implementation Priority

**Phase 1 (This session):**
1. Multi-line input ✓
2. Smart autocomplete ✓
3. Terminal plots (plotext) ✓
4. Token/cost tracking ✓
5. Enhanced syntax highlighting ✓
6. Status bar ✓

**Phase 2 (Next):**
7. Session export
8. Progressive disclosure
9. Query templates
10. Performance profiling

**Phase 3 (Future):**
11. Interactive TUI (Textual)
12. Bookmarks
13. Themes
14. Tutorial mode

---

## Technical Stack

**New Dependencies:**
```
plotext>=5.2.8        # Terminal plots
InquirerPy>=0.3.4     # Enhanced prompts & autocomplete
pygments>=2.17.0      # Syntax highlighting
tiktoken>=0.5.2       # Token counting
textual>=0.50.0       # TUI framework (future)
asciichartpy>=1.5.25  # Alternative charting
```

**Implementation Files:**
- `src/cli/chat_enhanced.py` - Enhanced chat with all features
- `src/cli/ui/` - UI components module
  - `ui/autocomplete.py` - Smart completion
  - `ui/plots.py` - Terminal plotting
  - `ui/status.py` - Status bar
  - `ui/multiline.py` - Multi-line input
  - `ui/themes.py` - Theme system
- `src/cli/tui/` - Full TUI mode (future)

---

## Success Metrics

**Quantitative:**
- 50% reduction in query formulation time (autocomplete)
- 80% of users use multi-line for complex queries
- 90% find visualizations helpful
- Zero users confused about costs (token tracking)

**Qualitative:**
- "Most delightful terminal app I've used"
- "Feels as good as Claude Code"
- "Visualization makes insights obvious"
- "I can finally explore my graph intuitively"

---

## Design Principles

1. **Progressive Enhancement** - Basic features work everywhere, enhanced features when available
2. **Transparency** - Always show what's happening (tools, costs, time)
3. **Forgiveness** - Easy undo, clear, reset
4. **Discoverability** - Autocomplete, suggestions, examples
5. **Efficiency** - Keyboard shortcuts, fast feedback
6. **Beauty** - Thoughtful design, pleasant to use for hours
7. **Accessibility** - Works in all terminals, themes, readable

---

## Inspiration Gallery

**Claude Code:**
- Streaming responses
- Clear tool separation
- Professional tone
- Token tracking

**GitHub CLI (gh):**
- Smart autocomplete
- Context awareness
- Keyboard shortcuts
- Beautiful tables

**k9s (Kubernetes TUI):**
- Interactive navigation
- Real-time updates
- Keyboard-driven
- Information density

**httpie:**
- Syntax highlighting
- Beautiful output
- User-friendly
- Progressive disclosure

**litecli/pgcli:**
- Autocomplete
- Multi-line mode
- Query history
- Syntax highlighting

---

Let's build the most delightful research terminal experience! 🚀
