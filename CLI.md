 🤖 Complete CLI Command Reference

  Main Command

  python claude_regulation_scraper.py [OPTIONS] COMMAND [ARGS]...

  Global Options:
  - --version - Show version and exit
  - -v, --verbose - Enable verbose output
  - --help - Show help message

  ---
  🔍 Discovery Commands

  discover jurisdictions - AI-powered source discovery

  python claude_regulation_scraper.py discover jurisdictions [OPTIONS]
  Options:
  - -j, --jurisdictions TEXT - Jurisdictions to discover (e.g., "Spain,Germany,Japan")
  - -a, --agencies TEXT - Specific agencies to focus on
  - -m, --methods TEXT - Discovery methods
  - -o, --output [table|json|csv] - Output format

  Examples:
  # Discover Spanish regulatory sources
  python claude_regulation_scraper.py discover jurisdictions -j Spain

  # Discover multiple jurisdictions
  python claude_regulation_scraper.py discover jurisdictions -j "Germany,France,Japan"

  # JSON output
  python claude_regulation_scraper.py discover jurisdictions -j Spain -o json

  discover domain - Analyze specific domain

  python claude_regulation_scraper.py discover domain [OPTIONS] URL
  Options:
  - --name TEXT - Website name
  - --jurisdiction TEXT - Jurisdiction code
  - --agency TEXT - Agency name
  - -o, --output [table|json|csv] - Output format

  ---
  📚 Source Management Commands

  sources list - List discovered sources

  python claude_regulation_scraper.py sources list [OPTIONS]
  Options:
  - -j, --jurisdiction TEXT - Filter by jurisdiction
  - -a, --agency TEXT - Filter by agency
  - -t, --type TEXT - Filter by source type
  - --active - Show only active sources
  - -o, --output [table|json|csv] - Output format

  Examples:
  # List all sources
  python claude_regulation_scraper.py sources list

  # List Spanish sources only
  python claude_regulation_scraper.py sources list -j Spain

  # List only active sources
  python claude_regulation_scraper.py sources list --active

  sources add - Manually add source

  python claude_regulation_scraper.py sources add [OPTIONS]
  Required Options:
  - --name TEXT - Source name
  - --url TEXT - Source URL
  - --type [rss_feed|api_endpoint|daily_listing|news_releases] - Source type
  - --jurisdiction TEXT - Jurisdiction
  - --agency TEXT - Agency name

  Optional:
  - --feed-url TEXT - RSS/API feed URL
  - --frequency [daily|weekly|monthly|real_time] - Update frequency

  sources validate - Validate source

  python claude_regulation_scraper.py sources validate SOURCE_ID

  ---
  📊 Monitoring Commands

  monitor run - Basic monitoring

  python claude_regulation_scraper.py monitor run [OPTIONS]
  Options:
  - --sources TEXT - Specific source IDs (comma-separated)
  - -j, --jurisdictions TEXT - Monitor jurisdictions
  - --compliance-only - Show only compliance regulations
  - --categories TEXT - Compliance categories to focus on
  - -o, --output [table|json|csv] - Output format

  Examples:
  # Monitor all Spanish sources
  python claude_regulation_scraper.py monitor run -j Spain

  # Monitor specific sources
  python claude_regulation_scraper.py monitor run --sources "source1,source2"

  # Compliance-focused monitoring
  python claude_regulation_scraper.py monitor run -j Spain --compliance-only

  monitor smart-extract - Advanced monitoring with AI

  python claude_regulation_scraper.py monitor smart-extract [OPTIONS]
  Options:
  - --sources TEXT - Source IDs to process
  - -j, --jurisdictions TEXT - Process jurisdictions
  - --optimize-patterns - Enable pattern optimization (default: enabled)
  - -o, --output [table|json] - Output format

  Examples:
  # Smart extraction for Spain with pattern optimization
  python claude_regulation_scraper.py monitor smart-extract -j Spain --optimize-patterns

  # Process specific sources
  python claude_regulation_scraper.py monitor smart-extract --sources "source1,source2"

  monitor insights - View learning analytics

  python claude_regulation_scraper.py monitor insights [OPTIONS]
  Options:
  - -j, --jurisdiction TEXT - Filter by jurisdiction
  - -s, --source TEXT - Filter by source ID
  - -d, --days INTEGER - Days to analyze (default: 7)
  - -o, --output [table|json] - Output format

  Examples:
  # Spanish learning insights (last 7 days)
  python claude_regulation_scraper.py monitor insights -j Spain -d 7

  # All jurisdictions (last 30 days)
  python claude_regulation_scraper.py monitor insights -d 30

  # JSON format for analysis
  python claude_regulation_scraper.py monitor insights -j Spain -o json

  monitor status - View monitoring status

  python claude_regulation_scraper.py monitor status [OPTIONS]
  Options:
  - -j, --jurisdiction TEXT - Filter by jurisdiction
  - -o, --output [table|json] - Output format

  monitor results - View discovered publications

  python claude_regulation_scraper.py monitor results [OPTIONS]
  Options:
  - --since TEXT - Results since date (YYYY-MM-DD)
  - -l, --limit INTEGER - Limit number of results
  - -j, --jurisdiction TEXT - Filter by jurisdiction
  - --compliance-only - Show only compliance regulations
  - --min-impact [critical|high|medium|low] - Minimum impact level
  - -o, --output [table|json|csv] - Output format

  ---
  🔗 Extraction Commands

  extract - Extract from specific URL

  python claude_regulation_scraper.py extract [OPTIONS] URL
  Options:
  - -o, --output [text|json|file] - Output format
  - --output-file TEXT - Save to file

  Examples:
  # Extract text from URL
  python claude_regulation_scraper.py extract https://example.gov/regulations

  # Save to file
  python claude_regulation_scraper.py extract https://example.gov/regs -o file --output-file regulations.txt

  ---
  ⚙️ Configuration Commands

  config show - Show current configuration

  python claude_regulation_scraper.py config show

  config set-api-key - Set API keys

  python claude_regulation_scraper.py config set-api-key [openai|firecrawl] API_KEY

  Examples:
  # Set OpenAI API key
  python claude_regulation_scraper.py config set-api-key openai sk-...

  # Set Firecrawl API key  
  python claude_regulation_scraper.py config set-api-key firecrawl fc-...

  ---
  🚀 Quick Start

  quick-start - Interactive setup guide

  python claude_regulation_scraper.py quick-start

  ---
  💡 Common Usage Workflows

  Complete New Setup:

  # 1. Quick start guide
  python claude_regulation_scraper.py quick-start

  # 2. Discover sources for your jurisdiction
  python claude_regulation_scraper.py discover jurisdictions -j Spain

  # 3. Run monitoring
  python claude_regulation_scraper.py monitor run -j Spain

  # 4. View learning insights
  python claude_regulation_scraper.py monitor insights -j Spain

  Daily Monitoring:

  # Smart extraction with learning
  python claude_regulation_scraper.py monitor smart-extract -j Spain --optimize-patterns

  # View results
  python claude_regulation_scraper.py monitor results -j Spain --since 2025-09-01

  # Check learning progress
  python claude_regulation_scraper.py monitor insights -j Spain -d 1

  Multi-Jurisdiction Setup:

  # Discover multiple jurisdictions
  python claude_regulation_scraper.py discover jurisdictions -j "Spain,Germany,France"

  # Monitor all
  python claude_regulation_scraper.py monitor smart-extract --optimize-patterns

  # View status
  python claude_regulation_scraper.py monitor status
