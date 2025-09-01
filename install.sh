#!/bin/bash
# Claude Regulation Scraper - Installation Script
set -e

echo "🤖 Claude Regulation Scraper - Installation Script"
echo "=================================================="

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ Found: $python_version"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is available
echo "📋 Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 is available"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    echo "✅ pip is available"
    PIP_CMD="pip"
else
    echo "❌ pip not found. Please install pip."
    exit 1
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
$PIP_CMD install click rich tabulate feedparser python-dateutil
$PIP_CMD install openai tiktoken pydantic requests beautifulsoup4 lxml
$PIP_CMD install firecrawl-py || echo "⚠️  Firecrawl installation failed (optional)"

echo "✅ Dependencies installed successfully"

# Make script executable
echo "🔧 Setting up CLI..."
chmod +x claude_regulation_scraper.py

# Create symlink if possible
if [[ "$EUID" -eq 0 ]] || [[ -w "/usr/local/bin" ]]; then
    echo "🔗 Creating system-wide command link..."
    ln -sf "$(pwd)/claude_regulation_scraper.py" /usr/local/bin/claude-reg
    echo "✅ You can now use 'claude-reg' from anywhere"
else
    echo "💡 To use 'claude-reg' from anywhere, run:"
    echo "   sudo ln -sf $(pwd)/claude_regulation_scraper.py /usr/local/bin/claude-reg"
    echo "   Or add this directory to your PATH"
fi

# Test installation
echo "🧪 Testing installation..."
if python3 claude_regulation_scraper.py --help > /dev/null 2>&1; then
    echo "✅ CLI is working correctly"
else
    echo "❌ CLI test failed"
    exit 1
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Set up your API keys:"
echo "      python3 claude_regulation_scraper.py config set-api-key openai YOUR_OPENAI_KEY"
echo ""
echo "   2. Run quick start:"
echo "      python3 claude_regulation_scraper.py quick-start"
echo ""
echo "   3. Discover sources:"
echo "      python3 claude_regulation_scraper.py discover jurisdictions --jurisdictions US"
echo ""
echo "📚 For full documentation, see INSTALLATION.md"