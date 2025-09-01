# 🤖 Claude Regulation Scraper

**Production-ready AI-powered CLI system for product compliance monitoring.** Automatically discovers regulatory publication sources, monitors daily for new regulations, and filters for product compliance relevance across jurisdictions.

## 🎯 **Problem Solved**

✅ **Core Challenge**: *"Monitor specific jurisdictions and return new regulations found for product compliance"*

✅ **Complete Solution**: 
- 🔍 **Automatic Discovery**: AI finds regulatory publication sources without hardcoded URLs
- 📊 **Daily Monitoring**: Tracks new regulations across US, UK, EU jurisdictions  
- 🎯 **Compliance-Only Mode**: `--compliance-only` flag filters for product safety, testing, certification
- 🏢 **Business Impact Classification**: Critical/High/Medium/Low impact levels
- 📋 **Team Integration**: JSON/CSV export for existing workflows
- 🛠️ **Production CLI**: Beautiful terminal interface with rich tables and progress tracking

## ✨ Key Features

- **Jurisdiction Monitoring**: US, UK, EU regulatory sources
- **Product Compliance Focus**: Filters for safety, testing, certification requirements
- **Beautiful CLI**: Rich terminal interface with progress bars and tables
- **Data Persistence**: Sources and results saved permanently
- **Export Capabilities**: JSON/CSV output for team workflows
- **Manual Source Management**: Add known regulatory sources easily

## 🏗️ Architecture

The system uses a multi-agent LLM architecture with specialized agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Monitoring Orchestrator            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Discovery  │  │ Change Detection │  │   Compliance    │  │
│  │    Agent    │  │      Agent       │  │ Classification  │  │
│  └─────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Firecrawl   │  │ Content         │  │    Vision       │  │
│  │ Extractor   │  │ Validation      │  │   Processing    │  │
│  └─────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                    ┌─────────────────────┐
                    │  Infrastructure     │
                    │  - Redis Caching    │
                    │  - Message Broker   │
                    │  - Configuration    │
                    └─────────────────────┘
```

## 🚀 Quick Start

### 1. Installation
```bash
# Automated installation
./install.sh

# Or manual setup
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Set API keys
python claude_regulation_scraper.py config set-api-key openai "your-openai-key"
python claude_regulation_scraper.py config set-api-key firecrawl "your-firecrawl-key"

# Verify setup
python claude_regulation_scraper.py config show
```

### 3. Start Monitoring
```bash
# Discover FDA sources automatically
python claude_regulation_scraper.py discover jurisdictions --jurisdictions US --agencies FDA

# Add known sources manually
python claude_regulation_scraper.py sources add \
  --name "FDA_News" \
  --url "https://www.fda.gov/news-events" \
  --type daily_listing \
  --jurisdiction US \
  --agency FDA

# Monitor for product compliance regulations
python claude_regulation_scraper.py monitor run --jurisdictions US --compliance-only

# View results
python claude_regulation_scraper.py monitor results --compliance-only --limit 20
```

## 📋 CLI Commands Overview

### Discovery Commands
```bash
# Discover sources by jurisdiction
python claude_regulation_scraper.py discover jurisdictions -j US,UK --agencies FDA,CPSC

# Analyze specific domains  
python claude_regulation_scraper.py discover domain https://www.fda.gov/news-events --jurisdiction US --agency FDA
```

### Source Management
```bash
# List all sources
python claude_regulation_scraper.py sources list

# Filter sources by jurisdiction
python claude_regulation_scraper.py sources list --jurisdiction US

# Add new source manually
python claude_regulation_scraper.py sources add --name "FDA News" --url "https://www.fda.gov/news-events" --type daily_listing --jurisdiction US --agency FDA

# Validate source functionality
python claude_regulation_scraper.py sources validate SOURCE_ID
```

### Monitoring & Results
```bash
# Monitor specific jurisdictions for compliance regulations
python claude_regulation_scraper.py monitor run -j US,UK --compliance-only --output table

# Monitor with business impact filtering (future feature)
python claude_regulation_scraper.py monitor run -j US --compliance-only --min-impact critical

# Check monitoring status  
python claude_regulation_scraper.py monitor status

# Export results for team workflows
python claude_regulation_scraper.py monitor run -j US,UK --compliance-only --output json > compliance_report.json
python claude_regulation_scraper.py monitor run -j US,UK --compliance-only --output csv > compliance_report.csv

# Export results as JSON
claude-reg monitor results --compliance-only --output json > compliance_regs.json
```

### Configuration
```bash
# Set API keys
claude-reg config set-api-key openai "your-key"

# Show current configuration
claude-reg config show

# Quick start guide
claude-reg quick-start
```

## 🎯 Product Compliance Features

### Compliance-Only Monitoring
```bash
# Monitor only product compliance regulations
claude-reg monitor run --jurisdictions US,UK,EU --compliance-only

# Filter by business impact
claude-reg monitor results --compliance-only --min-impact critical

# Focus on specific categories
claude-reg monitor run --compliance-only --categories "safety,testing,labeling"
```

### Rich Output for Compliance Teams
- **Business Impact**: Critical, High, Medium, Low classifications
- **Compliance Categories**: Safety, Testing, Certification, Labeling, etc.
- **Affected Products**: Electronics, Consumer Goods, Medical Devices
- **Implementation Timeline**: Effective dates and deadlines
- **Regulatory Requirements**: Testing, certification, documentation needs

## 💡 Real-World Usage Examples

### Daily Compliance Monitoring
```bash
# Morning routine - check for new compliance regulations
claude-reg monitor run --jurisdictions US,UK,EU --compliance-only --since yesterday

# Export for team review
claude-reg monitor results --compliance-only --output json > daily_compliance_$(date +%Y%m%d).json
```

### Jurisdiction-Specific Monitoring
```bash
# Monitor US FDA and CPSC
claude-reg sources list --jurisdiction US
claude-reg monitor run --jurisdictions US --compliance-only

# Monitor UK regulations
claude-reg sources add --name "UK_Safety" --url "https://www.gov.uk/product-safety" --type daily_listing --jurisdiction UK --agency "BEIS"
claude-reg monitor run --jurisdictions UK --compliance-only
```

### Integration with Existing Workflows
```bash
# CSV export for spreadsheets
claude-reg monitor results --compliance-only --output csv > compliance.csv

# Automated daily checks (cron job)
0 9 * * * claude-reg monitor run --jurisdictions US,UK --compliance-only --output json >> daily_compliance.log
```

## 🛠️ Prerequisites

- **Python 3.8+**
- **OpenAI API Key** (required)
- **Firecrawl API Key** (optional, for enhanced extraction)

### 1. Clone Repository

```bash
git clone <repository-url>
cd universal-regulation-scraper
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the project root:

```bash
# Required - OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Recommended - Firecrawl API Key (get free key at https://www.firecrawl.dev/)
FIRECRAWL_API_KEY=your-firecrawl-api-key-here

# Optional - Redis for production caching
REDIS_URL=redis://localhost:6379
```

### 4. Dependencies List

Create `requirements.txt`:

```
openai>=1.0.0
firecrawl-py>=4.0.0
aiohttp>=3.8.0
redis>=4.5.0
pydantic>=2.0.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
PyMuPDF>=1.23.0
python-dotenv>=1.0.0
tiktoken>=0.5.0
asyncio-throttle>=1.0.0
```

## 🚀 **Quick Start**

### Get Running in 3 Steps
```bash
# 1. Setup (one-time)
./install.sh
python claude_regulation_scraper.py config set-api-key openai "your-key"

# 2. Discover regulatory sources (AI-powered)
python claude_regulation_scraper.py discover jurisdictions -j "Spain,Germany,Japan"

# 3. Monitor for product compliance
python claude_regulation_scraper.py monitor run -j "Spain" --compliance-only
```

**🎯 That's it!** The AI automatically finds regulatory portals and monitors them for product compliance regulations.

📖 **Need more details?** See the [Complete Usage Guide](#-complete-usage-guide) below for:
- Starting from scratch vs. known sites scenarios
- Daily operations and persistence behavior  
- Compliance filtering options
- Team workflows and automation examples

## 📚 **Complete Usage Guide**

### **Scenario 1: Starting from Scratch (Don't Know the Sites)**

**Perfect for:** New users who need to discover regulatory sources for specific countries/jurisdictions.

#### Step 1: Initial Setup
```bash
# Configure your OpenAI API key (one-time setup)
python claude_regulation_scraper.py config set-api-key openai "your-openai-api-key"

# Verify configuration
python claude_regulation_scraper.py config show
```

#### Step 2: AI-Powered Discovery
```bash
# Discover regulatory sources for your jurisdictions using full country names
python claude_regulation_scraper.py discover jurisdictions -j "Spain,Germany,Japan"

# Or use abbreviations if you prefer
python claude_regulation_scraper.py discover jurisdictions -j "ES,DE,JP" 

# For US-specific agencies, you can filter
python claude_regulation_scraper.py discover jurisdictions -j "United States" -a "FDA,CPSC"
```

**What happens:** The AI automatically finds official government gazettes, regulatory portals, RSS feeds, and API endpoints for each country. No hardcoded limitations - works for any jurisdiction!

#### Step 3: Review Discovered Sources
```bash
# See everything the AI discovered
python claude_regulation_scraper.py sources list

# Filter by specific jurisdiction
python claude_regulation_scraper.py sources list --jurisdiction Spain

# Get detailed info about sources
python claude_regulation_scraper.py sources list --output json
```

#### Step 4: Start Monitoring
```bash
# Monitor for product compliance regulations only
python claude_regulation_scraper.py monitor run -j "Spain" --compliance-only

# Monitor all regulations (not just compliance)
python claude_regulation_scraper.py monitor run -j "Spain"

# Export results for your team
python claude_regulation_scraper.py monitor run -j "Spain,Germany" --compliance-only --output json > compliance_results.json
```

---

### **Scenario 2: You Already Know the Sites**

**Perfect for:** Users who have specific regulatory websites they want to monitor directly.

#### Add Known Sources Manually
```bash
# Add a specific regulatory source you know about
python claude_regulation_scraper.py sources add \
  --name "Spanish Official Gazette" \
  --url "https://www.boe.es" \
  --type daily_listing \
  --jurisdiction Spain \
  --agency "Spanish Government"

# Add an RSS feed you want to monitor
python claude_regulation_scraper.py sources add \
  --name "FDA Safety Alerts Feed" \
  --url "https://www.fda.gov/rss/safety-alerts.xml" \
  --type rss_feed \
  --jurisdiction "United States" \
  --agency "FDA"
```

#### Start Monitoring Immediately
```bash
# Monitor your manually added sources
python claude_regulation_scraper.py monitor run -j Spain --compliance-only

# Monitor specific sources by ID
python claude_regulation_scraper.py sources list  # Get source IDs
python claude_regulation_scraper.py monitor run --sources "abc123,def456"
```

## ⏰ **Daily Operations & Persistence**

### **"Will it collect regulations from today?"**
✅ **YES** - The system focuses on **recent and new** publications:
- Collects regulations published **today** and recent days
- Uses publication dates and "latest" sections from regulatory websites  
- Prioritizes **new** and **recent** content, not historical archives
- Looks for "Today's Publications," "Recent Updates," "Latest Releases" sections

### **"If I run again today, what happens?"**
✅ **Smart Deduplication** - Safe to run multiple times:
- **Won't show duplicates** - Same regulation won't appear twice
- **Change detection** - Only shows NEW items since last run
- **Content hashing** - Uses sophisticated deduplication algorithms
- **Safe to run hourly** - No duplicate processing or storage

### **"Is there persistence? What happens tomorrow?"**
✅ **Full Persistence** - Everything is saved and remembered:
- **Discovered sources persist** - Sources found today available tomorrow
- **Tomorrow shows only NEW** - Will show only regulations published since yesterday
- **Historical tracking** - Maintains record of everything you've seen
- **Cumulative discovery** - Sources accumulate over time, no re-discovery needed
- **Session continuity** - Monday's discovery available for Tuesday's monitoring

### **"Is it product compliance only?"**
🎯 **Configurable** - You control the scope:

#### All Regulations Mode (Default)
```bash
python claude_regulation_scraper.py monitor run -j Spain
```
Shows ALL regulatory announcements, news, gazettes, etc.

#### Product Compliance Mode  
```bash
python claude_regulation_scraper.py monitor run -j Spain --compliance-only
```
Shows ONLY regulations related to:
- Product safety requirements
- Testing and certification standards  
- Labeling and packaging rules
- Import/export compliance
- Manufacturing standards

#### AI Classification
- **LLM-powered filtering** - Uses advanced AI to identify product compliance relevance
- **Business impact levels** - Classifies as Critical/High/Medium/Low impact
- **Smart categorization** - Automatically sorts by safety, testing, certification, etc.

## 📅 **Daily Workflow Examples**

### Morning Compliance Check
```bash
# Quick overview of new compliance regulations across key jurisdictions
python claude_regulation_scraper.py monitor run -j "United States,Spain,Germany" --compliance-only

# Check monitoring status 
python claude_regulation_scraper.py monitor status
```

### Team Compliance Report
```bash
# Generate daily compliance report for your team
python claude_regulation_scraper.py monitor run -j "US,EU,UK" --compliance-only --output json > daily_$(date +%Y%m%d).json

# CSV format for spreadsheet analysis  
python claude_regulation_scraper.py monitor run -j "US,EU,UK" --compliance-only --output csv > daily_compliance.csv
```

### Weekly Full Discovery  
```bash
# Discover new regulatory sources for expanding markets
python claude_regulation_scraper.py discover jurisdictions -j "Canada,Australia,Brazil"

# Comprehensive monitoring across all discovered sources
python claude_regulation_scraper.py monitor run --compliance-only --output json > weekly_full_scan.json
```

### Automated Daily Operations
```bash
# Example cron job setup (crontab -e)
# Run every morning at 8 AM
0 8 * * * cd /path/to/scraper && python claude_regulation_scraper.py monitor run -j "US,EU,UK" --compliance-only --output json > /reports/daily_$(date +\%Y\%m\%d).json
```

## 💾 **Data Persistence & State Management**

### **What Gets Saved**
- ✅ **Discovered Sources** - All regulatory portals, feeds, APIs found by AI
- ✅ **Monitoring Results** - Each session's findings with timestamps
- ✅ **Content Hashes** - Deduplication data to prevent duplicate alerts
- ✅ **Source Metadata** - Confidence scores, update frequencies, agencies
- ✅ **Session History** - Complete audit trail of all discovery and monitoring activities

### **Cross-Session Behavior**
```bash
# Monday: Discover sources
python claude_regulation_scraper.py discover jurisdictions -j Spain

# Tuesday: Use Monday's sources for monitoring  
python claude_regulation_scraper.py monitor run -j Spain --compliance-only
# ↳ Uses sources discovered Monday, shows only NEW regulations from Tuesday

# Wednesday: Continuous monitoring
python claude_regulation_scraper.py monitor run -j Spain --compliance-only  
# ↳ Shows only NEW regulations published since Tuesday
```

### **Data Storage Locations**
- **Configuration**: `~/.claude_regulation_scraper/config.json`
- **Discovered Sources**: `~/.claude_regulation_scraper/data/publication_sources.json`
- **Monitoring Results**: `~/.claude_regulation_scraper/data/monitoring_sessions.json`
- **Discovery History**: `~/.claude_regulation_scraper/data/discovery_sessions.json`

### **Data Portability**
```bash
# Export all data for backup or migration
python claude_regulation_scraper.py sources list --output json > sources_backup.json

# View historical monitoring results
python claude_regulation_scraper.py monitor results --output json > results_history.json
```

## 📋 Core Features

### 1. Universal Regulation Extraction

**What it does**: Extract regulation content from any government or legal website URL

**Example Usage**:
```python
from src.agents.llm_agents.firecrawl_extractor_agent import FirecrawlExtractorAgent

# Initialize agent
extractor = FirecrawlExtractorAgent(broker=message_broker)

# Extract from any regulation URL
result = await extractor.extract_regulation_comprehensive(
    "https://www.legislation.gov.uk/ukpga/2018/12/section/1"
)

# Result contains:
# - Clean markdown content
# - Structured regulation data
# - Legal metadata
# - Quality assessment
```

**Supported Sources**:
- 🇺🇸 US Federal Register, CPSC, FDA regulations
- 🇬🇧 UK legislation.gov.uk, government publications  
- 🇪🇺 EUR-Lex, EU regulatory databases
- 🌍 Any government or regulatory website

### 2. Change Detection System

**What it does**: Monitor websites daily and detect meaningful changes in regulation content

**Key Features**:
- Content hashing for precise change detection
- AI-powered significance assessment
- Diff analysis with context
- No false positives

**Example Setup**:
```python
from src.agents.llm_agents.change_detection_agent import ChangeDetectionAgent

# Add monitoring target
await change_detector.add_monitoring_target(
    name="FDA Product Safety Alerts",
    url="https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
    website_type="regulatory_agency",
    monitoring_frequency="daily"
)

# Check for changes
changes = await change_detector.detect_changes(target_id, current_content)
```

### 3. Product Compliance Classification

**What it does**: Classify regulations for product compliance relevance and business impact

**Classification Categories**:
- `product_safety` - General product safety requirements
- `electrical_safety` - Electrical product safety (UL, IEC standards)
- `chemical_safety` - Chemical substances, RoHS, REACH
- `food_safety` - Food contact materials, additives
- `medical_device` - Medical device regulations, FDA requirements
- `automotive` - Vehicle safety, automotive standards
- `toys_children` - Children's product safety, toy regulations
- `textiles` - Textile safety, flammability standards
- `cosmetics` - Cosmetic product regulations
- `environmental` - Environmental impact, sustainability
- `cybersecurity` - IoT security, connected devices
- And more...

**Business Impact Levels**:
- `critical` - Immediate action required, product recalls possible
- `high` - Major compliance changes, significant business impact  
- `medium` - Moderate changes, planning required
- `low` - Minor changes, awareness needed
- `informational` - No direct compliance impact

**Example Usage**:
```python
from src.agents.llm_agents.compliance_classifier_agent import ComplianceClassifierAgent

classification = await classifier.classify_regulation(
    regulation_text=content,
    title="Consumer Product Safety Improvement Act",
    url=source_url,
    jurisdiction="US"
)

# Result includes:
# - Compliance relevance (True/False)
# - Primary category (e.g., "product_safety")
# - Business impact ("high", "medium", etc.)
# - Affected product types
# - Implementation timeline
# - Certification requirements
```

### 4. Daily Monitoring Orchestrator

**What it does**: Coordinate the complete daily monitoring workflow

**Workflow Steps**:
1. Load monitoring targets and schedules
2. Extract current content using Firecrawl
3. Detect changes using AI-powered analysis
4. Classify changes for product compliance relevance
5. Generate prioritized alerts for high-impact changes
6. Create comprehensive daily reports
7. Update baselines and monitoring data

**Example Usage**:
```python
from src.agents.llm_agents.daily_monitoring_orchestrator import DailyMonitoringOrchestrator

# Run daily monitoring
results = await orchestrator.run_daily_monitoring(
    focus_categories=["product_safety", "electrical_safety", "chemical_safety"]
)

# Results include:
# - Targets monitored
# - Changes detected  
# - Compliance-relevant changes
# - High-priority alerts
# - Detailed reports
```

## 🔧 Configuration

### Base Configuration (`config/base.yaml`)

```yaml
# OpenAI Configuration
openai:
  api_key: null  # Set via OPENAI_API_KEY environment variable
  default_model: "gpt-4o-mini"
  vision_model: "gpt-4o-mini"
  max_tokens: 4000
  temperature: 0.1

# Agent Configuration
agents:
  discovery:
    enabled: true
    max_concurrent_jobs: 3
    timeout: 60
    
  compliance_classifier:
    enabled: true
    confidence_threshold: 0.7
    focus_categories: ["product_safety", "electrical_safety"]

# Monitoring Configuration
monitoring:
  enabled: true
  health_check_interval: 60
  alert_thresholds:
    high_impact_changes: 5
    critical_changes: 1

# Performance Optimization
optimization:
  max_concurrent_requests: 20
  request_deduplication: true
  cache_aggressive: true
```

### Environment-Specific Configuration

Create environment-specific configs:
- `config/development.yaml` - Development settings
- `config/production.yaml` - Production settings  
- `config/testing.yaml` - Test settings

## 🧪 Testing

The system includes comprehensive testing suites:

### 1. Basic System Tests

```bash
# Test configuration and basic functionality
python test_simple_extraction.py
```

### 2. Full Regulation Extraction Tests

```bash
# Test complete extraction pipeline with real URLs
python test_full_regulation_extraction.py
```

### 3. Enhanced Firecrawl Tests

```bash
# Test Firecrawl-powered extraction
python test_firecrawl_extraction.py
```

### 4. Daily Monitoring Tests

```bash
# Test complete daily monitoring workflow
python test_daily_monitoring.py
```

## 📊 Usage Examples

### Example 1: Extract Single Regulation

```python
import asyncio
from src.agents.llm_agents.firecrawl_extractor_agent import FirecrawlExtractorAgent

async def extract_regulation():
    # Initialize broker and agent
    broker = MessageBroker()
    extractor = FirecrawlExtractorAgent(broker)
    
    # Extract regulation
    result = await extractor.extract_regulation_comprehensive(
        "https://www.legislation.gov.uk/ukpga/2018/12/section/1"
    )
    
    if result.get('success'):
        print(f"Extracted {result['content_stats']['content_length']} characters")
        print(f"Title: {result['scrape_data']['title']}")
        
        # Save to file
        with open('extracted_regulation.md', 'w') as f:
            f.write(result['scrape_data']['markdown'])
    
asyncio.run(extract_regulation())
```

### Example 2: Set Up Daily Monitoring

```python
import asyncio
from src.agents.llm_agents.daily_monitoring_orchestrator import DailyMonitoringOrchestrator

async def setup_monitoring():
    orchestrator = DailyMonitoringOrchestrator(broker=broker)
    
    # Set up common product safety targets
    await orchestrator.setup_monitoring_targets("product_safety")
    
    # Run daily monitoring
    results = await orchestrator.run_daily_monitoring()
    
    print(f"Monitored: {results['summary']['targets_monitored']} targets")
    print(f"Changes: {results['summary']['changes_detected']}")
    print(f"Alerts: {results['summary']['high_priority_alerts']}")

asyncio.run(setup_monitoring())
```

### Example 3: Classify Regulation for Compliance

```python
import asyncio
from src.agents.llm_agents.compliance_classifier_agent import ComplianceClassifierAgent

async def classify_regulation():
    classifier = ComplianceClassifierAgent(broker=broker)
    
    regulation_text = """
    The Consumer Product Safety Improvement Act requires all children's products
    to meet specific lead content limitations and phthalate restrictions.
    Third-party testing and certification is required.
    """
    
    result = await classifier.classify_regulation(
        regulation_text=regulation_text,
        title="Consumer Product Safety Improvement Act",
        url="https://www.cpsc.gov/Regulations-Laws--Standards/CPSIA",
        jurisdiction="US"
    )
    
    if result.get('is_relevant'):
        classification = result['classification']
        print(f"Category: {classification['primary_category']}")
        print(f"Impact: {classification['business_impact']}")  
        print(f"Products: {classification['affected_product_types']}")

asyncio.run(classify_regulation())
```

## 📁 Project Structure

```
universal-regulation-scraper/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env                              # Environment variables (create this)
│
├── config/                           # Configuration files
│   ├── base.yaml                     # Base configuration
│   ├── development.yaml              # Development settings
│   └── production.yaml               # Production settings
│
├── src/                              # Source code
│   ├── config/                       # Configuration management
│   │   └── config_manager.py         # Config loading and validation
│   │
│   ├── infrastructure/               # Infrastructure components
│   │   ├── caching/                  # Caching system
│   │   │   └── cache_manager.py      # Redis + local caching
│   │   └── message_broker.py         # Agent coordination
│   │
│   ├── models/                       # Data models
│   │   ├── regulation_models.py      # Regulation data structures
│   │   └── extraction_models.py      # Extraction result models
│   │
│   └── agents/                       # LLM Agents
│       ├── llm_agents/               # Specialized LLM agents
│       │   ├── base_agent.py         # Base agent class
│       │   ├── discovery_llm_agent.py        # Website analysis
│       │   ├── firecrawl_extractor_agent.py  # Enhanced extraction
│       │   ├── change_detection_agent.py     # Change monitoring
│       │   ├── compliance_classifier_agent.py # Compliance classification
│       │   └── daily_monitoring_orchestrator.py # Workflow coordination
│       │
│       └── coordination/             # Agent coordination
│           └── agent_coordinator.py  # Multi-agent workflows
│
├── tests/                            # Test files
│   ├── test_simple_extraction.py     # Basic functionality tests
│   ├── test_full_regulation_extraction.py # Complete extraction tests
│   ├── test_firecrawl_extraction.py  # Firecrawl-enhanced tests
│   └── test_daily_monitoring.py      # Daily monitoring tests
│
├── daily_monitoring_data/            # Monitoring data storage
│   ├── monitoring_targets.json       # Configured targets
│   ├── change_history.json          # Change detection history
│   └── baselines/                    # Content baselines
│
├── daily_monitoring_reports/         # Generated reports
│   └── daily_monitoring_YYYYMMDD.json # Daily reports
│
├── firecrawl_extraction_results/     # Extraction results
│   └── regulation_content_*.md       # Extracted regulations
│
└── logs/                             # Application logs
    └── regulation_scraper.log        # Main log file
```

## 🔍 How It Works

### 1. Content Extraction Pipeline

```
URL Input → Firecrawl Scraping → Content Cleaning → AI Analysis → Structured Output
     ↓              ↓                    ↓             ↓              ↓
  Any Regulation   Clean Markdown    Remove Noise   GPT-4 Analysis   JSON + Files
     URL          + Metadata        + Validation   + Classification  + Reports
```

### 2. Change Detection Workflow

```
Target URL → Content Extraction → Hash Comparison → Diff Analysis → AI Assessment
     ↓              ↓                    ↓              ↓              ↓
 Monitoring      Current Content     Change Detection   Text Diff    Significance 
  Target         vs Baseline         (Hash-based)    Generation      Score
```

### 3. Compliance Classification Process

```
Regulation Text → AI Analysis → Category Classification → Impact Assessment → Alert Generation
       ↓              ↓                   ↓                     ↓                  ↓
   Full Content   GPT-4 Analysis    Product Compliance    Business Impact      Priority
   + Metadata     + Legal Context    Categories (20+)     (Critical/High/...)   Alerts
```

## 🚀 Production Deployment

### 1. Production Configuration

Set up production environment:

```bash
# Production environment variables
export ENVIRONMENT=production
export OPENAI_API_KEY=your-production-key
export FIRECRAWL_API_KEY=your-production-key
export REDIS_URL=redis://your-redis-server:6379
```

### 2. Daily Monitoring Schedule

Set up automated daily monitoring with cron:

```bash
# Add to crontab for daily 6 AM monitoring
0 6 * * * cd /path/to/app && python -c "
import asyncio
from src.agents.llm_agents.daily_monitoring_orchestrator import DailyMonitoringOrchestrator
async def run(): 
    orchestrator = DailyMonitoringOrchestrator(broker=None)
    await orchestrator.run_daily_monitoring()
asyncio.run(run())
"
```

### 3. Production Monitoring

Monitor system health and performance:
- **Logs**: Check `logs/regulation_scraper.log`
- **Reports**: Review daily reports in `daily_monitoring_reports/`
- **Alerts**: Monitor high-priority compliance alerts
- **Performance**: Track extraction success rates and timing

## 🔧 Customization

### Add New Monitoring Targets

```python
# Add custom regulatory websites
await change_detector.add_monitoring_target(
    name="Custom Regulatory Site",
    url="https://your-regulatory-site.gov/updates",
    website_type="regulatory_agency",
    monitoring_frequency="daily",
    change_indicators=["Updated:", "New Regulation:", "Amendment:"]
)
```

### Extend Compliance Categories

Add new product categories in `compliance_classifier_agent.py`:

```python
class ComplianceCategory(str, Enum):
    # Existing categories...
    CUSTOM_INDUSTRY = "custom_industry"
    SPECIALIZED_PRODUCT = "specialized_product"
```

### Custom Classification Rules

Modify classification logic for specific business needs:

```python
# In ComplianceClassifierAgent._classify_regulation()
if "your-specific-keyword" in regulation_text.lower():
    classification.business_impact = BusinessImpact.CRITICAL
    classification.primary_category = ComplianceCategory.CUSTOM_INDUSTRY
```

## 📈 Performance & Scaling

### Performance Metrics

- **Extraction Speed**: ~3-15 seconds per regulation (depends on content size)
- **Change Detection**: ~1-5 seconds per target
- **Classification**: ~2-8 seconds per regulation  
- **Daily Monitoring**: ~5-30 seconds for 5-20 targets

### Scaling Considerations

- **Concurrent Processing**: System supports 5-20 concurrent extractions
- **Rate Limiting**: Built-in delays prevent API overload
- **Caching**: Redis caching reduces redundant processing
- **Error Recovery**: Automatic retry with exponential backoff

### Resource Requirements

- **Memory**: 1-4 GB RAM (depends on content volume)
- **Storage**: 100 MB - 10 GB (depends on monitoring history)
- **API Costs**: ~$0.01-0.10 per regulation extraction (OpenAI + Firecrawl)

## 🛡️ Security & Compliance

### Data Security

- **API Keys**: Stored in environment variables only
- **Content Storage**: Local filesystem (configurable)
- **Logging**: No sensitive data logged
- **Access Control**: File-system based permissions

### Legal Compliance

- **Robots.txt**: System respects robots.txt directives
- **Rate Limiting**: Conservative request rates to avoid overloading servers
- **User Agent**: Identifies as research/compliance tool
- **Content Caching**: Minimal retention for change detection only

## 🆘 Troubleshooting

### Common Issues

**1. OpenAI API Key Issues**
```bash
Error: OpenAI API key required
Solution: Set OPENAI_API_KEY environment variable
```

**2. Firecrawl API Errors**
```bash
Error: Firecrawl client not initialized
Solution: Sign up at firecrawl.dev and set FIRECRAWL_API_KEY
```

**3. Content Extraction Failures**
```bash
Error: No content extracted
Solution: Check URL accessibility and website structure
```

**4. Redis Connection Issues**
```bash
Warning: Failed to connect to Redis
Solution: Install Redis or use local caching only
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

- **Slow Extraction**: Increase timeout values in config
- **Memory Usage**: Reduce concurrent processing limits  
- **API Rate Limits**: Increase request delays in agent configs

## 📚 API Reference

### FirecrawlExtractorAgent

```python
class FirecrawlExtractorAgent:
    async def extract_regulation_comprehensive(url: str) -> Dict[str, Any]
    async def _firecrawl_scrape(url: str, include_raw_html: bool = False) -> Dict[str, Any]
    async def _analyze_regulation_structure(content: str, url: str) -> Dict[str, Any]
    async def _extract_legal_metadata(content: str, url: str) -> Dict[str, Any]
```

### ChangeDetectionAgent

```python
class ChangeDetectionAgent:
    async def add_monitoring_target(name: str, url: str, website_type: str) -> Dict[str, Any]
    async def detect_changes(target_id: str, current_content: str) -> Dict[str, Any]
    async def get_change_summary(days_back: int = 7) -> Dict[str, Any]
```

### ComplianceClassifierAgent

```python
class ComplianceClassifierAgent:
    async def classify_regulation(regulation_text: str, title: str, url: str) -> Dict[str, Any]
    async def filter_compliance_relevant(regulation_summaries: List[Dict]) -> Dict[str, Any]
```

### DailyMonitoringOrchestrator

```python
class DailyMonitoringOrchestrator:
    async def run_daily_monitoring(target_ids: List[str] = None) -> Dict[str, Any]
    async def setup_monitoring_targets(target_type: str = "product_safety") -> Dict[str, Any]
    async def generate_monitoring_report(report_period_days: int = 1) -> Dict[str, Any]
```

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI** - For GPT-4o-mini language model
- **Firecrawl** - For enhanced web scraping capabilities  
- **Government Data Sources** - For providing accessible regulation data
- **Open Source Community** - For the underlying libraries and tools

---

## 🆘 Support

For questions, issues, or feature requests:

- **Documentation**: This README and inline code comments
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Email**: [contact@yourcompany.com] for enterprise support

**Happy Regulation Monitoring! 🚀**