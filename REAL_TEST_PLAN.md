# 🧪 Real-World Testing Plan for RGE

**Date**: 2025-11-06
**Status**: Ready to execute
**Tester**: Claude Code
**Environment**: Production API keys configured

---

## 🎯 Testing Philosophy

**"Real queries break things that tests don't catch"**

- Start small, build confidence
- Monitor everything
- Expect failures, fix quickly
- Document all issues
- Validate at each stage

---

## 📋 Pre-Flight Checklist

- [x] API keys configured (.env)
- [x] Config check passes (both Anthropic & OpenAI detected)
- [x] Ontology file exists (ml_research.yaml)
- [ ] Test directory created
- [ ] Logging enabled

---

## 🧪 Test Stages

### Stage 1: Minimal Discover (5 papers)
**Research Question**: "graph neural networks for recommendation systems"

**Why this question?**
- Specific enough (not too broad)
- Active research area (papers exist)
- Technical topic (good for ML ontology)
- Manageable scope

**Expected outcomes:**
- 5 seed papers generated
- Papers have: title, abstract, authors, year
- Relevance scores > 0.6
- JSON output file created

**Monitoring:**
- API calls to Semantic Scholar
- LLM relevance scoring calls
- Error messages
- Time taken (~30-60 seconds expected)

**Success criteria:**
- ✓ Completes without crashing
- ✓ Returns 5 valid papers
- ✓ Output JSON is well-formed
- ✓ No API errors

**Potential issues:**
- Rate limiting from Semantic Scholar
- LLM API failures
- Missing paper metadata
- JSON serialization errors

---

### Stage 2: Extract Knowledge (from Stage 1 papers)
**Input**: Stage 1 output (papers.json)
**Ontology**: ml_research.yaml

**Expected outcomes:**
- Knowledge graph created
- Entities extracted: Methods, Datasets, Findings
- Relationships identified
- Graph saved as JSON

**Monitoring:**
- PDF downloads (may fail for some papers)
- Text extraction quality
- LLM extraction calls
- Entity parsing
- Graph construction

**Success criteria:**
- ✓ Knowledge graph created
- ✓ At least some entities extracted
- ✓ Graph is queryable
- ✓ No crashes on missing data

**Potential issues:**
- PDF download failures (403, 404)
- PDF parsing errors
- LLM extraction timeouts
- Entity validation failures
- Relationship parsing issues

---

### Stage 3: Interactive Chat
**Input**: Knowledge graph from Stage 2

**Test queries:**
1. "What papers are in this graph?"
2. "What methods are mentioned?"
3. "Find gaps in the research"
4. "Show me connections between papers"

**Expected outcomes:**
- Agent loads successfully
- Responds to queries
- Uses graph tools
- Provides insights

**Success criteria:**
- ✓ Chat session starts
- ✓ Agent responds coherently
- ✓ Can query the graph
- ✓ Tools execute successfully

**Potential issues:**
- Agent initialization failures
- Tool execution errors
- Graph query failures
- LLM response issues

---

## 🔍 Monitoring Checklist

During each stage, watch for:

- [ ] Console output (errors in red)
- [ ] API call status
- [ ] File creation (intermediate files)
- [ ] Memory usage
- [ ] Time elapsed
- [ ] Cost tracking (API calls)

---

## 🐛 Known Risk Areas

Based on code review:

1. **Semantic Scholar API**
   - Rate limits (100 requests/5min without key)
   - Missing paper metadata
   - Network timeouts

2. **PDF Processing**
   - Download failures (many papers don't have PDFs)
   - Parsing errors
   - Large file handling

3. **LLM Calls**
   - Timeout on long papers
   - Rate limits
   - Cost accumulation
   - JSON parsing from responses

4. **Graph Construction**
   - Entity validation
   - Relationship parsing
   - Duplicate handling
   - Graph serialization

---

## 📊 Success Metrics

### Minimal Success (MVP)
- Discovers 5 papers
- Extracts at least 1 entity
- Chat loads and responds once

### Good Success
- Discovers 5 papers with metadata
- Extracts 10+ entities and relationships
- Chat handles 3/4 test queries

### Excellent Success
- Full pipeline works end-to-end
- Rich knowledge graph
- Agent provides insights
- No manual fixes needed

---

## 🛠️ Debugging Strategy

If something breaks:

1. **Don't panic** - This is expected
2. **Check the error** - Read the full stacktrace
3. **Check the data** - Look at intermediate files
4. **Isolate the issue** - Which component failed?
5. **Fix** - Add error handling, validate data
6. **Re-test** - Try the stage again
7. **Document** - Record the issue and fix

---

## 📝 Test Execution Log

### Stage 1: Discover
- **Start time**: _pending_
- **End time**: _pending_
- **Status**: Not started
- **Papers found**: _pending_
- **Issues**: _pending_
- **Fixes applied**: _pending_

### Stage 2: Extract
- **Start time**: _pending_
- **End time**: _pending_
- **Status**: Not started
- **Entities extracted**: _pending_
- **Issues**: _pending_
- **Fixes applied**: _pending_

### Stage 3: Chat
- **Start time**: _pending_
- **End time**: _pending_
- **Status**: Not started
- **Queries tested**: _pending_
- **Issues**: _pending_
- **Fixes applied**: _pending_

---

## 🎓 Lessons Learned

_To be filled during testing..._

---

**Ready to begin! Let's run Stage 1! 🚀**
