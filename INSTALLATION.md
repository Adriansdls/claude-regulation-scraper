# 🤖 Claude Regulation Scraper - Installation Guide

## Overview

Claude Regulation Scraper is an AI-powered system for discovering and monitoring regulatory publication sources. It automatically finds where new regulations are published daily across jurisdictions and provides intelligent monitoring capabilities.

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- (Optional) Firecrawl API key for enhanced web scraping

## Quick Installation

### 1. Clone/Download the Repository
```bash
git clone <repository-url>
cd claude-regulation-scraper
```

### 2. Install Dependencies
```bash
# Using make (recommended)
make deps

# Or using pip directly
pip install -r requirements.txt
```

### 3. Set Up API Keys
```bash
# Interactive setup
make setup

# Or manually
export OPENAI_API_KEY="your-openai-api-key"
export FIRECRAWL_API_KEY="your-firecrawl-api-key"  # Optional
```

### 4. Install CLI Tool
```bash
# Install in development mode
make install-dev

# Or install normally
make install
```

### 5. Test Installation
```bash
claude-reg --help
claude-reg quick-start
```

## Manual Installation Steps

### Step 1: Python Environment Setup
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install click rich tabulate feedparser python-dateutil
pip install openai tiktoken redis pydantic requests beautifulsoup4
pip install firecrawl-py  # Optional but recommended
```

### Step 2: Configure API Keys
```bash
# Set environment variables
export OPENAI_API_KEY="sk-proj-your-key-here"
export FIRECRAWL_API_KEY="fc-your-key-here"  # Optional

# Or use the CLI configuration
python claude_regulation_scraper.py config set-api-key openai "your-key"
python claude_regulation_scraper.py config set-api-key firecrawl "your-key"
```

### Step 3: Verify Installation
```bash
python claude_regulation_scraper.py --help
python claude_regulation_scraper.py config show
```

## Usage Examples

### 1. Quick Start
```bash
# Show quick start guide
claude-reg quick-start

# Discover sources for US jurisdictions
claude-reg discover jurisdictions --jurisdictions US --agencies FDA,CPSC

# List discovered sources
claude-reg sources list

# Run monitoring
claude-reg monitor run --jurisdictions US
```

### 2. Source Management
```bash
# Add a manual source
claude-reg sources add \
  --name "FDA RSS Feed" \
  --url "https://www.fda.gov/rss.xml" \
  --type rss_feed \
  --jurisdiction US \
  --agency FDA \
  --frequency daily

# Validate a source
claude-reg sources validate fda_rss_feed_0

# List sources with filters
claude-reg sources list --jurisdiction US --agency FDA
```

### 3. Domain Analysis
```bash
# Analyze a specific domain for publication sources
claude-reg discover domain https://www.fda.gov/news-events \
  --name "FDA News" \
  --jurisdiction US \
  --agency FDA
```

### 4. Content Extraction
```bash
# Extract regulations from a URL
claude-reg extract https://www.legislation.gov.uk/uksi/2019/419/regulation/1

# Save to file
claude-reg extract https://example.com/regulation \
  --output file \
  --output-file regulation.txt
```

### 5. Monitoring and Results
```bash
# Check monitoring status
claude-reg monitor status

# View recent results
claude-reg monitor results --since 2024-01-01 --limit 20

# Export results as JSON
claude-reg monitor results --output json > results.json
```

## Configuration

### Configuration File Location
- **Linux/Mac**: `~/.claude_regulation_scraper/config.json`
- **Windows**: `%USERPROFILE%\.claude_regulation_scraper\config.json`

### Data Storage Location
- **Linux/Mac**: `~/.claude_regulation_scraper/data/`
- **Windows**: `%USERPROFILE%\.claude_regulation_scraper\data\`

### Configuration Options
```json
{
  "openai_api_key": "your-key",
  "firecrawl_api_key": "your-key",
  "storage_path": "/path/to/data",
  "default_jurisdictions": ["US", "UK", "EU"],
  "default_agencies": ["FDA", "CPSC", "EPA"],
  "output_format": "table",
  "verbose": false
}
```

## Development Setup

### For Contributors
```bash
# Clone repository
git clone <repository-url>
cd claude-regulation-scraper

# Install in development mode
make install-dev

# Run tests
make test
make test-cli

# Format code
make lint
```

### Testing
```bash
# Run comprehensive tests
python test_publication_discovery_system.py
python test_cli_functionality.py

# Test individual components
python test_simple_discovery.py
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

**2. API Key Issues**
```bash
# Verify API key is set
claude-reg config show

# Test API connectivity
claude-reg extract https://www.example.com --output text
```

**3. Permission Errors**
```bash
# Check storage directory permissions
ls -la ~/.claude_regulation_scraper/

# Create directory if needed
mkdir -p ~/.claude_regulation_scraper/data
```

**4. Redis Connection (if using advanced features)**
```bash
# Install and start Redis
brew install redis  # Mac
sudo apt-get install redis-server  # Ubuntu

# Start Redis
redis-server
```

### Getting Help
```bash
# Command help
claude-reg --help
claude-reg discover --help
claude-reg sources --help

# Verbose output for debugging
claude-reg -v sources list
```

## Advanced Usage

### Automated Monitoring
```bash
# Set up cron job for daily monitoring
echo "0 9 * * * claude-reg monitor run --jurisdictions US,UK" | crontab -
```

### Batch Operations
```bash
# Bulk add sources from CSV
# (Future feature - manual implementation needed)

# Export configuration
claude-reg config show --output json > config-backup.json
```

### Integration with Other Tools
```bash
# Pipe results to other commands
claude-reg sources list --output csv | grep FDA

# Use with jq for JSON processing
claude-reg monitor results --output json | jq '.[] | select(.relevance > 0.8)'
```

## Next Steps

1. **Set up API keys** using `make setup`
2. **Run discovery** with `claude-reg discover jurisdictions`  
3. **Add manual sources** for specific agencies you monitor
4. **Set up monitoring** with `claude-reg monitor run`
5. **Check results regularly** with `claude-reg monitor results`

For more advanced features, see the full documentation and consider setting up the web interface and API gateway components.