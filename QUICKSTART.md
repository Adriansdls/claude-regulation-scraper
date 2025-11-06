# Quick Start - Test Installation Now!

**3 minutes to test if the package is shareable** ⚡

---

## Method 1: Quick Local Test (Fastest)

**Test without installing:**

```bash
# Just run the CLI directly
python -m src.cli.main --help

# Should show:
# Usage: main [OPTIONS] COMMAND [ARGS]...
# Commands:
#   discover  Discover research papers
#   extract   Extract knowledge from papers
#   chat      Interactive chat with agent
```

**Works?** ✅ Package structure is correct!

---

## Method 2: Install Locally (3 commands)

**Install in editable mode:**

```bash
# 1. Install package
pip install -e .

# 2. Test the command
rge --help

# 3. Verify everything
python scripts/verify_install.py
```

**See "rge" command?** ✅ Installation system works!

---

## Method 3: Share with Yourself (Test Distribution)

**Simulate sending to a colleague:**

```bash
# 1. Build wheel
pip install build
python -m build

# 2. "Send" the wheel (simulate)
cp dist/research_graph_explorer-2.0.0-py3-none-any.whl /tmp/

# 3. Install from "received" wheel
pip install /tmp/research_graph_explorer-2.0.0-py3-none-any.whl

# 4. Test
rge --help
```

**Works?** ✅ Package is distributable!

---

## ✅ Quick Verification

After any method, run:

```bash
# Check command exists
rge --version

# Check all systems
python scripts/verify_install.py

# Test chat (with dummy graph)
echo '{"papers":[],"entities":[],"relationships":[]}' > test.json
rge chat test.json
# Press Ctrl+C to exit
```

---

## Expected Output

**rge --help should show:**
```
Usage: rge [OPTIONS] COMMAND [ARGS]...

  Research Graph Explorer CLI

Options:
  --help  Show this message and exit.

Commands:
  chat      Interactive chat with Network Science Agent
  discover  Discover research papers
  extract   Extract knowledge from papers
```

---

## 🚀 You're Done!

**If any method worked:**
- ✅ Package is shareable!
- ✅ Ready to send to colleagues
- ✅ Ready for team use

**Share via:**
- Git: `pip install git+https://github.com/...`
- Wheel: Email the `.whl` file
- Folder: Zip and share, they run `pip install .`

See **INSTALL.md** for detailed options!
