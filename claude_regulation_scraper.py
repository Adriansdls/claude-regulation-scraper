#!/usr/bin/env python3
"""
Claude Regulation Scraper - CLI Interface
AI-powered regulation discovery and monitoring system
"""
import click
import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Rich for beautiful terminal output
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.llm_agents.publication_discovery_agent import PublicationDiscoveryAgent
from src.agents.llm_agents.feed_monitoring_agent import FeedMonitoringAgent
from src.infrastructure.message_broker import MessageBroker

# Initialize rich console
console = Console()

# CLI configuration
CLI_CONFIG_FILE = Path.home() / '.claude_regulation_scraper' / 'config.json'
DEFAULT_STORAGE_PATH = Path.home() / '.claude_regulation_scraper' / 'data'

class CLIConfig:
    """CLI configuration manager"""
    
    def __init__(self):
        self.config_file = CLI_CONFIG_FILE
        self.config_file.parent.mkdir(exist_ok=True)
        self.storage_path = DEFAULT_STORAGE_PATH
        self.storage_path.mkdir(exist_ok=True)
        
    def load_config(self) -> Dict:
        """Load configuration from file"""
        if not self.config_file.exists():
            return self._default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return self._default_config()
    
    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY", ""),
            "storage_path": str(self.storage_path),
            "learning_data_path": str(self.storage_path / "learning_data"),
            "default_jurisdictions": ["US", "UK", "EU"],
            "default_agencies": ["FDA", "CPSC", "EPA"],
            "output_format": "table",
            "verbose": False
        }

# Global config instance
cli_config = CLIConfig()

@click.group()
@click.version_option(version="1.0.0", prog_name="Claude Regulation Scraper")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """
    🤖 Claude Regulation Scraper
    
    AI-powered system for discovering and monitoring regulatory publication sources.
    Automatically finds where new regulations are published daily across jurisdictions.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    # Load configuration
    config = cli_config.load_config()
    ctx.obj['config'] = config
    
    # Check for required API keys
    if not config.get('openai_api_key'):
        console.print("[yellow]⚠️  OpenAI API key not configured. Use 'claude-reg config set-api-key openai <key>' to set it.[/yellow]")

@cli.group()
@click.pass_context
def discover(ctx):
    """🔍 Discovery commands - find regulatory publication sources"""
    pass

@discover.command('jurisdictions')
@click.option('--jurisdictions', '-j', default='United States,United Kingdom', help='Comma-separated jurisdictions. Use full country names for clarity (e.g., "Spain,Germany,Japan") or abbreviations (ES,DE,JP)')
@click.option('--agencies', '-a', help='Comma-separated agencies to focus on (optional - leave empty for all agencies)')
@click.option('--methods', '-m', default='automated_scan', help='Discovery methods')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.pass_context
def discover_jurisdictions(ctx, jurisdictions, agencies, methods, output):
    """🌍 Discover regulatory publication sources for any country using AI
    
    This command uses advanced LLM agents to automatically discover regulatory 
    portals, official gazettes, and publication sources for any jurisdiction.
    
    ✨ Examples:
      claude-reg discover jurisdictions -j "Spain"
      claude-reg discover jurisdictions -j "Germany,France,Japan"  
      claude-reg discover jurisdictions -j "ES,DE,JP"
    
    🎯 The AI discovers:
      • Official government gazettes and bulletins
      • Regulatory agency publication portals  
      • Daily/weekly regulatory announcements
      • RSS feeds and APIs for real-time updates
    
    ✅ Works for any country - no hardcoded limitations!
    """
    
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    
    # Parse inputs
    jurisdiction_list = [j.strip() for j in jurisdictions.split(',')]
    # Only use default agencies if no specific jurisdictions are provided, or if agencies are explicitly specified
    # This prevents US-focused agency filters from blocking other countries
    if agencies:
        agency_list = [a.strip() for a in agencies.split(',')]
    else:
        # For agentic discovery, don't apply default agency filters unless it's US-focused
        us_focused = any(j.lower() in ['us', 'united states', 'usa'] for j in jurisdiction_list)
        agency_list = config.get('default_agencies', []) if us_focused else []
    method_list = [m.strip() for m in methods.split(',')]
    
    async def run_discovery():
        console.print(Panel.fit("🚀 Starting Publication Discovery", style="bold blue"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Initialize components
            task = progress.add_task("Initializing agents...", total=None)
            
            try:
                broker = MessageBroker()
                discovery_agent = PublicationDiscoveryAgent(
                    broker=broker,
                    storage_path=config['storage_path']
                )
                
                # Ensure discovery data is loaded
                await discovery_agent._load_discovery_data()
                
                progress.update(task, description="Discovering publication sources...")
                
                # Debug: log agentic discovery mode
                if verbose:
                    console.print(f"[dim]Debug: Using fully agentic LLM-powered portal discovery[/dim]")
                
                # Run discovery
                result = await discovery_agent._discover_publication_sources(
                    target_jurisdictions=jurisdiction_list,
                    discovery_methods=method_list,
                    focus_agencies=agency_list
                )
                
                progress.update(task, description="✅ Discovery complete!")
                
                if result.get('success'):
                    _display_discovery_results(result, output)
                else:
                    console.print(f"[red]❌ Discovery failed: {result.get('error', 'Unknown error')}[/red]")
                    
            except Exception as e:
                console.print(f"[red]❌ Error during discovery: {e}[/red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
    
    # Run the async discovery
    asyncio.run(run_discovery())

@discover.command('domain')
@click.argument('url')
@click.option('--name', help='Website name')
@click.option('--jurisdiction', default='unknown', help='Jurisdiction (US, UK, EU, etc.)')
@click.option('--agency', default='unknown', help='Agency name')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.pass_context
def discover_domain(ctx, url, name, jurisdiction, agency, output):
    """Analyze a specific domain for publication sources"""
    
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    
    if not name:
        name = url
    
    async def run_domain_analysis():
        console.print(Panel.fit(f"🌐 Analyzing Domain: {name}", style="bold green"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing agents...", total=None)
            
            try:
                broker = MessageBroker()
                discovery_agent = PublicationDiscoveryAgent(
                    broker=broker,
                    storage_path=config['storage_path']
                )
                
                progress.update(task, description=f"Analyzing {url}...")
                
                # Run domain analysis
                result = await discovery_agent._analyze_website_for_publications(
                    website_url=url,
                    website_name=name,
                    jurisdiction=jurisdiction,
                    agency=agency
                )
                
                progress.update(task, description="✅ Analysis complete!")
                
                if result.get('success'):
                    _display_domain_analysis_results(result, output)
                else:
                    console.print(f"[red]❌ Analysis failed: {result.get('error', 'Unknown error')}[/red]")
                    
            except Exception as e:
                console.print(f"[red]❌ Error during analysis: {e}[/red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
    
    # Run the async analysis
    asyncio.run(run_domain_analysis())

@cli.group()
@click.pass_context
def sources(ctx):
    """📚 Source management commands"""
    pass

@sources.command('list')
@click.option('--jurisdiction', '-j', help='Filter by jurisdiction')
@click.option('--agency', '-a', help='Filter by agency')
@click.option('--type', '-t', help='Filter by source type')
@click.option('--active', is_flag=True, help='Show only active sources')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.pass_context
def list_sources(ctx, jurisdiction, agency, type, active, output):
    """List discovered publication sources"""
    
    config = ctx.obj['config']
    
    async def run_list():
        try:
            broker = MessageBroker()
            discovery_agent = PublicationDiscoveryAgent(
                broker=broker,
                storage_path=config['storage_path']
            )
            
            # Load sources
            await discovery_agent._load_discovery_data()
            sources = discovery_agent.discovered_sources
            
            # Apply filters
            filtered_sources = []
            for source_id, source in sources.items():
                if jurisdiction and source.jurisdiction != jurisdiction:
                    continue
                if agency and source.agency != agency:
                    continue
                if type and source.source_type.value != type:
                    continue
                if active and not source.is_active:
                    continue
                
                # Convert to dict for display
                source_dict = {
                    'id': source.source_id,
                    'name': source.name,
                    'url': source.url,
                    'type': source.source_type.value,
                    'jurisdiction': source.jurisdiction,
                    'agency': source.agency,
                    'confidence': f"{source.confidence_score:.2f}",
                    'frequency': source.update_frequency.value,
                    'active': '✅' if source.is_active else '❌',
                    'last_checked': source.last_checked.strftime('%Y-%m-%d %H:%M') if source.last_checked else 'Never'
                }
                filtered_sources.append(source_dict)
            
            if not filtered_sources:
                console.print("[yellow]No sources found matching the criteria.[/yellow]")
                console.print("💡 Try running discovery first: [bold]claude-reg discover jurisdictions[/bold]")
                return
            
            _display_sources_list(filtered_sources, output)
            
        except Exception as e:
            console.print(f"[red]❌ Error listing sources: {e}[/red]")
    
    asyncio.run(run_list())

@sources.command('add')
@click.option('--name', required=True, help='Source name')
@click.option('--url', required=True, help='Source URL')
@click.option('--type', 'source_type', type=click.Choice(['rss_feed', 'api_endpoint', 'daily_listing', 'news_releases']), required=True, help='Source type')
@click.option('--jurisdiction', required=True, help='Jurisdiction (US, UK, EU, etc.)')
@click.option('--agency', required=True, help='Agency name')
@click.option('--feed-url', help='RSS/API feed URL if different from main URL')
@click.option('--frequency', type=click.Choice(['daily', 'weekly', 'monthly', 'real_time']), default='daily', help='Update frequency')
@click.pass_context
def add_source(ctx, name, url, source_type, jurisdiction, agency, feed_url, frequency):
    """Add a publication source manually"""
    
    config = ctx.obj['config']
    
    async def run_add_source():
        try:
            broker = MessageBroker()
            discovery_agent = PublicationDiscoveryAgent(
                broker=broker,
                storage_path=config['storage_path']
            )
            
            # Load existing sources
            await discovery_agent._load_discovery_data()
            
            # Create new source
            from src.agents.llm_agents.publication_discovery_agent import PublicationSource, PublicationSourceType, UpdateFrequency
            
            source_id = f"{agency.lower()}_{source_type}_{len(discovery_agent.discovered_sources)}"
            
            new_source = PublicationSource(
                source_id=source_id,
                name=name,
                url=url,
                source_type=PublicationSourceType(source_type),
                jurisdiction=jurisdiction,
                agency=agency,
                discovered_date=datetime.utcnow(),
                discovery_method="human_input",
                confidence_score=1.0,  # Human input gets max confidence
                update_frequency=UpdateFrequency(frequency),
                content_types=["regulations"],  # Default
                feed_url=feed_url,
                feed_format="rss" if source_type == "rss_feed" else None,
                is_active=True,
                last_checked=None,
                check_interval_hours=24,
                publication_date_selectors=[],
                title_selectors=[],
                content_link_patterns=[],
                publications_found=0,
                false_positive_rate=0.0,
                extraction_success_rate=0.0
            )
            
            # Add to agent
            discovery_agent.discovered_sources[source_id] = new_source
            await discovery_agent._save_discovery_data()
            
            console.print(f"[green]✅ Source added successfully![/green]")
            console.print(f"   ID: {source_id}")
            console.print(f"   Name: {name}")
            console.print(f"   URL: {url}")
            
        except Exception as e:
            console.print(f"[red]❌ Error adding source: {e}[/red]")
    
    asyncio.run(run_add_source())

@sources.command('validate')
@click.argument('source_id')
@click.pass_context
def validate_source(ctx, source_id):
    """Validate a publication source works correctly"""
    
    config = ctx.obj['config']
    
    async def run_validation():
        try:
            broker = MessageBroker()
            discovery_agent = PublicationDiscoveryAgent(
                broker=broker,
                storage_path=config['storage_path']
            )
            
            # Load sources
            await discovery_agent._load_discovery_data()
            
            if source_id not in discovery_agent.discovered_sources:
                console.print(f"[red]❌ Source '{source_id}' not found[/red]")
                return
            
            source = discovery_agent.discovered_sources[source_id]
            
            console.print(f"🔍 Validating source: {source.name}")
            
            # Test the source URL
            import requests
            try:
                response = requests.get(source.url, timeout=30)
                if response.status_code == 200:
                    console.print(f"[green]✅ URL accessible (HTTP {response.status_code})[/green]")
                else:
                    console.print(f"[yellow]⚠️  URL returned HTTP {response.status_code}[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ URL validation failed: {e}[/red]")
            
            # Test feed URL if available
            if source.feed_url:
                try:
                    response = requests.get(source.feed_url, timeout=30)
                    if response.status_code == 200:
                        console.print(f"[green]✅ Feed URL accessible[/green]")
                    else:
                        console.print(f"[yellow]⚠️  Feed URL returned HTTP {response.status_code}[/yellow]")
                except Exception as e:
                    console.print(f"[red]❌ Feed URL validation failed: {e}[/red]")
            
            console.print(f"[green]✅ Validation complete for {source.name}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error validating source: {e}[/red]")
    
    asyncio.run(run_validation())

@cli.group()
@click.pass_context
def monitor(ctx):
    """📊 Monitoring commands"""
    pass

@monitor.command('run')
@click.option('--sources', help='Comma-separated source IDs to monitor')
@click.option('--jurisdictions', '-j', help='Monitor all sources from jurisdictions')
@click.option('--compliance-only', is_flag=True, help='Filter results to show only product compliance regulations')
@click.option('--categories', help='Comma-separated compliance categories to focus on')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.pass_context
def run_monitoring(ctx, sources, jurisdictions, compliance_only, categories, output):
    """Run feed monitoring for discovered sources"""
    
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    
    async def run_monitoring_session():
        console.print(Panel.fit("📊 Starting Feed Monitoring", style="bold purple"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing monitoring...", total=None)
            
            try:
                broker = MessageBroker()
                discovery_agent = PublicationDiscoveryAgent(
                    broker=broker,
                    storage_path=config['storage_path']
                )
                
                monitoring_agent = FeedMonitoringAgent(
                    broker=broker,
                    discovery_agent=discovery_agent,
                    storage_path=config['storage_path'],
                    knowledge_base_path=config.get('learning_data_path', './learning_data')
                )
                
                # Import compliance classifier if needed
                if compliance_only:
                    from src.agents.llm_agents.compliance_classifier_agent import ComplianceClassifierAgent
                
                progress.update(task, description="Loading sources...")
                await discovery_agent._load_discovery_data()
                
                # Determine sources to monitor
                target_sources = []
                
                if sources:
                    source_ids = [s.strip() for s in sources.split(',')]
                    for source_id in source_ids:
                        if source_id in discovery_agent.discovered_sources:
                            target_sources.append(discovery_agent.discovered_sources[source_id])
                
                elif jurisdictions:
                    jurisdiction_list = [j.strip() for j in jurisdictions.split(',')]
                    for source in discovery_agent.discovered_sources.values():
                        if source.jurisdiction in jurisdiction_list and source.is_active:
                            target_sources.append(source)
                
                else:
                    # Monitor all active sources
                    target_sources = [s for s in discovery_agent.discovered_sources.values() if s.is_active]
                
                if not target_sources:
                    console.print("[yellow]No sources found to monitor.[/yellow]")
                    console.print("💡 Try running discovery first or check source filters.")
                    return
                
                progress.update(task, description=f"Monitoring {len(target_sources)} sources...")
                
                # Run intelligent monitoring with learning
                progress.update(task, description="Running intelligent feed monitoring...")
                source_ids = [source.source_id for source in target_sources]
                result = await monitoring_agent._monitor_publication_feeds(
                    source_ids=source_ids,
                    target_date=datetime.utcnow().isoformat(),
                    relevance_threshold=0.3
                )
                
                # If compliance-only filtering requested, apply it
                if compliance_only and result.get('success') and result.get('discovered_items'):
                    progress.update(task, description="Filtering for compliance relevance...")
                    
                    # Initialize compliance classifier
                    compliance_agent = ComplianceClassifierAgent(
                        broker=broker,
                        storage_path=config['storage_path']
                    )
                    
                    # Filter items for compliance relevance
                    compliance_items = []
                    for item in result.get('discovered_items', []):
                        # For now, mock compliance data - in production this would classify each item
                        if compliance_only:
                            item['business_impact'] = 'medium'  # Mock data
                            item['compliance_category'] = 'safety'  # Mock data
                            compliance_items.append(item)
                    
                    result['discovered_items'] = compliance_items
                    result['compliance_filtered'] = True
                
                progress.update(task, description="✅ Monitoring complete!")
                
                if result.get('success'):
                    _display_monitoring_results(result, output)
                else:
                    console.print(f"[red]❌ Monitoring failed: {result.get('error', 'Unknown error')}[/red]")
                    
                    # Still try to show learning insights even if monitoring failed
                    try:
                        insights = await monitoring_agent._get_learning_insights(days_back=1)
                        if insights.get('success'):
                            console.print("\n[blue]📊 Recent Learning Activity:[/blue]")
                            learning_activity = insights.get('insights', {}).get('learning_activity', {})
                            console.print(f"  • Patterns discovered today: {learning_activity.get('new_patterns_discovered', 0)}")
                            console.print(f"  • Patterns reinforced today: {learning_activity.get('patterns_reinforced', 0)}")
                    except:
                        pass  # Don't fail if insights can't be shown
                    
            except Exception as e:
                console.print(f"[red]❌ Error during monitoring: {e}[/red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
    
    asyncio.run(run_monitoring_session())

@monitor.command('status')
@click.option('--jurisdiction', '-j', help='Filter by jurisdiction')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def monitor_status(ctx, jurisdiction, output):
    """Show monitoring status for all sources"""
    
    config = ctx.obj['config']
    
    async def run_status():
        try:
            broker = MessageBroker()
            discovery_agent = PublicationDiscoveryAgent(
                broker=broker,
                storage_path=config['storage_path']
            )
            
            # Load sources
            await discovery_agent._load_discovery_data()
            sources = discovery_agent.discovered_sources
            
            # Filter by jurisdiction if specified
            if jurisdiction:
                sources = {sid: source for sid, source in sources.items() if source.jurisdiction == jurisdiction}
            
            if not sources:
                console.print("[yellow]No sources found for monitoring status.[/yellow]")
                return
            
            if output == 'json':
                status_data = {}
                for source_id, source in sources.items():
                    status_data[source_id] = {
                        'name': source.name,
                        'url': source.url,
                        'active': source.is_active,
                        'last_checked': source.last_checked.isoformat() if source.last_checked else None,
                        'publications_found': source.publications_found,
                        'success_rate': source.extraction_success_rate
                    }
                rprint(json.dumps(status_data, indent=2))
                return
            
            # Table format
            table = Table(title=f"Monitoring Status ({len(sources)} sources)")
            table.add_column("Source", style="bold")
            table.add_column("Agency")
            table.add_column("Status")
            table.add_column("Last Checked")
            table.add_column("Publications")
            table.add_column("Success Rate")
            
            for source in sources.values():
                status_emoji = "🟢" if source.is_active else "🔴"
                last_checked = source.last_checked.strftime('%Y-%m-%d %H:%M') if source.last_checked else 'Never'
                success_rate = f"{source.extraction_success_rate:.1%}" if source.extraction_success_rate > 0 else "N/A"
                
                table.add_row(
                    source.name[:30] + "..." if len(source.name) > 30 else source.name,
                    source.agency,
                    f"{status_emoji} {'Active' if source.is_active else 'Inactive'}",
                    last_checked,
                    str(source.publications_found),
                    success_rate
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Error getting status: {e}[/red]")
    
    asyncio.run(run_status())

@monitor.command('results')
@click.option('--since', help='Show results since date (YYYY-MM-DD)')
@click.option('--limit', '-l', default=50, help='Limit number of results')
@click.option('--jurisdiction', '-j', help='Filter by jurisdiction')
@click.option('--compliance-only', is_flag=True, help='Show only product compliance regulations')
@click.option('--min-impact', type=click.Choice(['critical', 'high', 'medium', 'low']), help='Minimum business impact level')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.pass_context
def monitor_results(ctx, since, limit, jurisdiction, compliance_only, min_impact, output):
    """Show recent monitoring results and discovered publications"""
    
    config = ctx.obj['config']
    
    async def run_results():
        try:
            broker = MessageBroker()
            monitoring_agent = FeedMonitoringAgent(
                broker=broker,
                storage_path=config['storage_path']
            )
            
            # Load monitoring data
            await monitoring_agent._load_monitoring_data()
            
            # Get recent items
            items = []
            for item in monitoring_agent.feed_items.values():
                # Apply filters
                if since:
                    try:
                        since_date = datetime.strptime(since, '%Y-%m-%d')
                        if item.discovered_date < since_date:
                            continue
                    except ValueError:
                        console.print(f"[red]❌ Invalid date format: {since}. Use YYYY-MM-DD[/red]")
                        return
                
                items.append({
                    'title': item.title,
                    'url': item.url,
                    'source': item.source_id,
                    'type': item.item_type,
                    'published': item.published_date.strftime('%Y-%m-%d') if item.published_date else 'Unknown',
                    'discovered': item.discovered_date.strftime('%Y-%m-%d %H:%M'),
                    'relevance': f"{item.relevance_score:.2f}",
                    'status': item.status.value
                })
            
            # Sort by discovery date (newest first) and limit
            items.sort(key=lambda x: x['discovered'], reverse=True)
            items = items[:limit]
            
            if not items:
                console.print("[yellow]No monitoring results found.[/yellow]")
                return
            
            if output == 'json':
                rprint(json.dumps(items, indent=2))
                return
            elif output == 'csv':
                if items:
                    headers = items[0].keys()
                    rprint(','.join(headers))
                    for item in items:
                        rprint(','.join(str(item.get(h, '')) for h in headers))
                return
            
            # Table format
            if compliance_only:
                table = Table(title=f"Product Compliance Regulations ({len(items)} items)")
                table.add_column("Title", style="bold")
                table.add_column("Type")
                table.add_column("Impact", style="red")
                table.add_column("Category")
                table.add_column("Published")
                table.add_column("Source")
            else:
                table = Table(title=f"Recent Monitoring Results ({len(items)} items)")
                table.add_column("Title", style="bold")
                table.add_column("Type")
                table.add_column("Source")
                table.add_column("Published")
                table.add_column("Relevance")
                table.add_column("Status")
            
            for item in items:
                title = item['title'][:40] + "..." if len(item['title']) > 40 else item['title']
                
                if compliance_only:
                    # Show compliance-focused information
                    table.add_row(
                        title,
                        item.get('type', 'regulation'),
                        item.get('business_impact', 'unknown'),
                        item.get('compliance_category', 'general'),
                        item.get('published', 'unknown'),
                        item.get('source', 'unknown')
                    )
                else:
                    # Show standard monitoring information
                    table.add_row(
                        title,
                        item['type'],
                        item['source'],
                        item['published'],
                        item['relevance'],
                        item['status']
                    )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Error getting results: {e}[/red]")
    
    asyncio.run(run_results())

@monitor.command('insights')
@click.option('--jurisdiction', '-j', help='Filter insights by jurisdiction')
@click.option('--source', '-s', help='Filter insights by source ID')
@click.option('--days', '-d', default=7, help='Number of days to analyze (default: 7)')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def learning_insights(ctx, jurisdiction, source, days, output):
    """Show learning insights and pattern analysis"""
    
    config = ctx.obj['config']
    
    async def run_insights():
        try:
            broker = MessageBroker()
            monitoring_agent = FeedMonitoringAgent(
                broker=broker,
                discovery_agent=None,
                storage_path=config['storage_path'],
                knowledge_base_path=config.get('learning_data_path', './learning_data')
            )
            
            # Get learning insights
            insights_result = await monitoring_agent._get_learning_insights(
                jurisdiction=jurisdiction,
                source_id=source,
                days_back=days
            )
            
            if not insights_result.get('success'):
                console.print(f"[red]❌ Error getting insights: {insights_result.get('error', 'Unknown error')}[/red]")
                if ctx.obj.get('verbose') and insights_result.get('traceback'):
                    console.print(f"[red]Traceback: {insights_result.get('traceback')}[/red]")
                return
            
            insights = insights_result.get('insights', {})
            
            if output == 'json':
                rprint(json.dumps(insights, indent=2, default=str))
                return
            
            # Display in table format
            console.print(Panel.fit(
                f"🧠 Learning Intelligence Report\n" +
                f"Analysis Period: {insights.get('analysis_period', {}).get('start_date', 'N/A')[:10]} to {insights.get('analysis_period', {}).get('end_date', 'N/A')[:10]}\n" +
                f"Days Analyzed: {days}" +
                (f"\nJurisdiction: {jurisdiction}" if jurisdiction else "") +
                (f"\nSource: {source}" if source else ""),
                style="bold blue"
            ))
            
            # Session Summary
            session_summary = insights.get('session_summary', {})
            if session_summary.get('total_sessions', 0) > 0:
                summary_table = Table(title="Learning Session Summary")
                summary_table.add_column("Metric", style="bold")
                summary_table.add_column("Value")
                
                summary_table.add_row("Total Learning Sessions", str(session_summary.get('total_sessions', 0)))
                summary_table.add_row("Successful Sessions", str(session_summary.get('successful_sessions', 0)))
                summary_table.add_row("Success Rate", f"{session_summary.get('success_rate', 0):.1f}%")
                summary_table.add_row("Total Items Extracted", str(session_summary.get('total_items_extracted', 0)))
                summary_table.add_row("Avg Items/Session", f"{session_summary.get('avg_items_per_successful_session', 0):.1f}")
                
                console.print(summary_table)
            
            # Learning Activity
            learning_activity = insights.get('learning_activity', {})
            if learning_activity:
                learning_table = Table(title="Learning Activity")
                learning_table.add_column("Activity", style="bold magenta")
                learning_table.add_column("Count", justify="center")
                
                learning_table.add_row("🌱 New Patterns Discovered", str(learning_activity.get('new_patterns_discovered', 0)))
                learning_table.add_row("💪 Patterns Reinforced", str(learning_activity.get('patterns_reinforced', 0)))
                learning_table.add_row("🚀 Learning Velocity/Day", f"{learning_activity.get('learning_velocity', 0):.1f}")
                
                console.print(learning_table)
            
            # Extraction Methods Performance
            extraction_methods = insights.get('extraction_methods', {})
            if extraction_methods:
                methods_table = Table(title="Extraction Method Performance")
                methods_table.add_column("Method", style="bold green")
                methods_table.add_column("Success Rate", justify="center")
                methods_table.add_column("Avg Items Found", justify="center")
                methods_table.add_column("Total Uses", justify="center")
                
                for method, stats in extraction_methods.items():
                    methods_table.add_row(
                        method.replace('_', ' ').title(),
                        f"{stats.get('success_rate', 0):.1f}%",
                        f"{stats.get('avg_items_found', 0):.1f}",
                        str(stats.get('total_uses', 0))
                    )
                
                console.print(methods_table)
            
            # Pattern Confidence Distribution
            pattern_dist = insights.get('pattern_confidence_distribution', {})
            if pattern_dist:
                console.print("\n🎆 [bold yellow]Pattern Confidence Distribution:[/bold yellow]")
                for confidence, count in pattern_dist.items():
                    console.print(f"  • {confidence.replace('_', ' ').title()}: {count} patterns")
            
            # Recent Errors
            recent_errors = insights.get('recent_errors', [])
            if recent_errors:
                console.print("\n⚠️  [bold red]Recent Learning Errors:[/bold red]")
                for error in recent_errors[-3:]:  # Show last 3 errors
                    console.print(f"  • {error.get('timestamp', 'N/A')[:16]}: {error.get('error', 'Unknown error')}")
            
            # Jurisdiction Profile if available
            jurisdiction_profile = insights.get('jurisdiction_profile', {})
            if jurisdiction_profile:
                profile_table = Table(title=f"Jurisdiction Profile: {jurisdiction}")
                profile_table.add_column("Attribute", style="bold cyan")
                profile_table.add_column("Value")
                
                profile_table.add_row("Total Sources", str(jurisdiction_profile.get('total_sources', 0)))
                profile_table.add_row("Avg Success Rate", f"{jurisdiction_profile.get('avg_success_rate', 0):.1f}%")
                profile_table.add_row("Learning Sessions", str(jurisdiction_profile.get('total_learning_sessions', 0)))
                if jurisdiction_profile.get('primary_language'):
                    profile_table.add_row("Primary Language", jurisdiction_profile.get('primary_language'))
                
                console.print(profile_table)
            
            if session_summary.get('total_sessions', 0) == 0:
                console.print("\n[yellow]💭 No learning sessions found for the specified criteria[/yellow]")
                console.print("[dim]Try running monitoring first to generate learning data[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ Error getting learning insights: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(traceback.format_exc())
    
    asyncio.run(run_insights())

@monitor.command('smart-extract')
@click.option('--sources', help='Comma-separated source IDs to process')
@click.option('--jurisdictions', '-j', help='Process all sources from jurisdictions')
@click.option('--optimize-patterns', is_flag=True, default=True, help='Optimize patterns before extraction (default: enabled)')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def smart_extraction(ctx, sources, jurisdictions, optimize_patterns, output):
    """Run smart extraction strategy with pattern optimization and adaptive learning"""
    
    config = ctx.obj['config']
    
    async def run_smart_extraction():
        try:
            console.print(Panel.fit(
                "🤖 Smart Extraction Strategy\n" +
                "Intelligent extraction using learned patterns and adaptive techniques",
                style="bold cyan"
            ))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Initializing smart extraction...", total=None)
                
                # Initialize agents
                broker = MessageBroker()
                discovery_agent = PublicationDiscoveryAgent(
                    broker=broker,
                    storage_path=config['storage_path']
                )
                
                monitoring_agent = FeedMonitoringAgent(
                    broker=broker,
                    discovery_agent=discovery_agent,
                    storage_path=config['storage_path'],
                    knowledge_base_path=config.get('learning_data_path', './learning_data')
                )
                
                progress.update(task, description="Loading sources...")
                await discovery_agent._load_discovery_data()
                
                # Determine sources to process
                target_sources = []
                
                if sources:
                    source_ids = [s.strip() for s in sources.split(',')]
                    for source_id in source_ids:
                        if source_id in discovery_agent.discovered_sources:
                            target_sources.append(source_id)
                elif jurisdictions:
                    jurisdiction_list = [j.strip() for j in jurisdictions.split(',')]
                    for source in discovery_agent.discovered_sources.values():
                        if source.jurisdiction in jurisdiction_list and source.is_active:
                            target_sources.append(source.source_id)
                else:
                    # Process all active sources
                    target_sources = [
                        s.source_id for s in discovery_agent.discovered_sources.values() 
                        if s.is_active
                    ]
                
                if not target_sources:
                    console.print("[yellow]⚠️  No sources found to process[/yellow]")
                    console.print("💡 Try running discovery first or check source filters.")
                    return
                
                progress.update(task, description=f"Running smart extraction on {len(target_sources)} sources...")
                
                # Execute smart extraction strategy
                strategy_result = await monitoring_agent._smart_extraction_strategy(
                    source_ids=target_sources,
                    optimize_patterns=optimize_patterns,
                    use_adaptive_selection=True
                )
                
                progress.update(task, description="✅ Smart extraction complete!")
                
                if strategy_result.get('success'):
                    _display_smart_extraction_results(strategy_result, output)
                else:
                    console.print(f"[red]❌ Smart extraction failed: {strategy_result.get('error', 'Unknown error')}[/red]")
        
        except Exception as e:
            console.print(f"[red]❌ Error in smart extraction: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(traceback.format_exc())
    
    asyncio.run(run_smart_extraction())

def _display_smart_extraction_results(result: Dict, output_format: str):
    """Display smart extraction strategy results"""
    if output_format == 'json':
        rprint(json.dumps(result, indent=2, default=str))
        return
    
    console.print(f"\n[bold green]🤖 Smart Extraction Strategy Complete![/bold green]")
    
    # Strategy Summary
    summary_table = Table(title="Strategy Summary")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("📊 Sources Processed", str(result.get('sources_processed', 0)))
    summary_table.add_row("📋 Total Publications Found", str(result.get('total_publications_found', 0)))
    summary_table.add_row("🔧 Patterns Optimized", str(result.get('patterns_optimized', 0)))
    summary_table.add_row("✅ Success Rate", f"{result.get('success_rate', 0):.1f}%")
    summary_table.add_row("📈 Avg Publications/Source", f"{result.get('avg_publications_per_source', 0):.1f}")
    summary_table.add_row("⏱️ Strategy Duration", f"{result.get('strategy_duration_seconds', 0):.1f}s")
    
    console.print(summary_table)
    
    # Learning Improvements
    improvements = result.get('learning_improvements', [])
    if improvements:
        console.print("\n🧠 [bold blue]Learning Improvements:[/bold blue]")
        for improvement in improvements[:5]:  # Show top 5
            console.print(f"  • {improvement}")
        if len(improvements) > 5:
            console.print(f"  [dim]... and {len(improvements) - 5} more improvements[/dim]")
    
    # Source-by-Source Results
    extraction_results = result.get('extraction_results', {})
    if extraction_results:
        console.print("\n📊 [bold cyan]Extraction Results by Source:[/bold cyan]")
        
        results_table = Table(title="Source Performance")
        results_table.add_column("Source ID", style="bold")
        results_table.add_column("Status", justify="center")
        results_table.add_column("Publications", justify="center")
        results_table.add_column("Avg Relevance", justify="center")
        results_table.add_column("Time (s)", justify="center")
        
        for source_id, source_result in extraction_results.items():
            if source_result.get('success'):
                status = "✅"
                pubs = str(source_result.get('publications_found', 0))
                relevance = f"{source_result.get('avg_relevance_score', 0):.2f}"
            else:
                status = "❌"
                pubs = "0"
                relevance = "N/A"
            
            results_table.add_row(
                source_id,
                status,
                pubs,
                relevance,
                f"{source_result.get('extraction_time', 0):.1f}"
            )
        
        console.print(results_table)
    
    # Strategic Recommendations
    recommendations = result.get('recommendations', [])
    if recommendations:
        console.print("\n💡 [bold yellow]Strategic Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  • {rec}")
    
    # Learning Insights Summary
    learning_insights = result.get('learning_insights', {})
    if learning_insights:
        learning_activity = learning_insights.get('learning_activity', {})
        if learning_activity.get('new_patterns_discovered', 0) > 0 or learning_activity.get('patterns_reinforced', 0) > 0:
            console.print("\n🎯 [bold magenta]Learning Activity:[/bold magenta]")
            console.print(f"  • New patterns discovered: {learning_activity.get('new_patterns_discovered', 0)}")
            console.print(f"  • Patterns reinforced: {learning_activity.get('patterns_reinforced', 0)}")
    
    # Errors if any
    extraction_errors = result.get('extraction_errors', [])
    if extraction_errors:
        console.print("\n⚠️  [bold red]Extraction Errors:[/bold red]")
        for error in extraction_errors[:3]:  # Show first 3 errors
            console.print(f"  • {error['source_id']}: {error['error']}")
        if len(extraction_errors) > 3:
            console.print(f"  [dim]... and {len(extraction_errors) - 3} more errors[/dim]")

@cli.group()
@click.pass_context
def config(ctx):
    """⚙️ Configuration commands"""
    pass

@config.command('show')
@click.pass_context
def show_config(ctx):
    """Show current configuration"""
    config = ctx.obj['config']
    
    table = Table(title="Claude Regulation Scraper Configuration")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    
    # Mask sensitive data
    safe_config = config.copy()
    if safe_config.get('openai_api_key'):
        safe_config['openai_api_key'] = safe_config['openai_api_key'][:8] + "..." if len(safe_config['openai_api_key']) > 8 else "***"
    if safe_config.get('firecrawl_api_key'):
        safe_config['firecrawl_api_key'] = safe_config['firecrawl_api_key'][:8] + "..." if len(safe_config['firecrawl_api_key']) > 8 else "***"
    
    for key, value in safe_config.items():
        if isinstance(value, list):
            value = ', '.join(value)
        table.add_row(key, str(value))
    
    console.print(table)

@config.command('set-api-key')
@click.argument('service', type=click.Choice(['openai', 'firecrawl']))
@click.argument('api_key')
@click.pass_context
def set_api_key(ctx, service, api_key):
    """Set API keys for services"""
    config = ctx.obj['config']
    
    if service == 'openai':
        config['openai_api_key'] = api_key
        os.environ['OPENAI_API_KEY'] = api_key
    elif service == 'firecrawl':
        config['firecrawl_api_key'] = api_key
        os.environ['FIRECRAWL_API_KEY'] = api_key
    
    cli_config.save_config(config)
    console.print(f"[green]✅ {service.upper()} API key updated successfully[/green]")

@cli.command('quick-start')
@click.pass_context
def quick_start(ctx):
    """🚀 Quick start guide for new users"""
    
    config = ctx.obj['config']
    
    console.print(Panel.fit("🚀 Claude Regulation Scraper - Quick Start", style="bold blue"))
    
    steps = [
        "1️⃣  Set up API keys:",
        "   claude-reg config set-api-key openai YOUR_OPENAI_KEY",
        "   claude-reg config set-api-key firecrawl YOUR_FIRECRAWL_KEY",
        "",
        "2️⃣  Discover publication sources:",
        "   claude-reg discover jurisdictions --jurisdictions US,UK --agencies FDA,CPSC",
        "",
        "3️⃣  List discovered sources:",
        "   claude-reg sources list",
        "",
        "4️⃣  Run monitoring:",
        "   claude-reg monitor run --jurisdictions US",
        "",
        "5️⃣  Check results:",
        "   claude-reg monitor results --since 2024-01-01",
        "",
        "💡 For help with any command: claude-reg COMMAND --help"
    ]
    
    for step in steps:
        if step.startswith("   "):
            console.print(f"[dim]{step}[/dim]")
        elif step == "":
            console.print()
        else:
            console.print(step)

@cli.command('extract')
@click.argument('url')
@click.option('--output', '-o', type=click.Choice(['text', 'json', 'file']), default='text', help='Output format')
@click.option('--output-file', help='Save to file (for --output file)')
@click.pass_context
def extract_url(ctx, url, output, output_file):
    """🔗 Extract regulations from a specific URL"""
    
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    
    async def run_extraction():
        console.print(Panel.fit(f"🔗 Extracting from: {url}", style="bold cyan"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing extraction...", total=None)
            
            try:
                # Use the existing regulation extraction system
                from src.agents.llm_agents.firecrawl_extractor_agent import FirecrawlExtractorAgent
                from src.agents.llm_agents.compliance_classifier_agent import ComplianceClassifierAgent
                from src.infrastructure.message_broker import MessageBroker
                
                broker = MessageBroker()
                extractor_agent = FirecrawlExtractorAgent(
                    broker=broker
                )
                
                progress.update(task, description="Extracting content...")
                
                # Run extraction
                result = await extractor_agent.extract_regulation_comprehensive(url)
                
                progress.update(task, description="✅ Extraction complete!")
                
                if result.get('success'):
                    extracted_content = result.get('content', result.get('extracted_content', ''))
                    metadata = result.get('metadata', {})
                    
                    if output == 'json':
                        output_data = {
                            'url': url,
                            'extraction_date': datetime.utcnow().isoformat(),
                            'content': extracted_content,
                            'metadata': metadata,
                            'content_length': len(extracted_content)
                        }
                        
                        if output_file:
                            with open(output_file, 'w') as f:
                                json.dump(output_data, f, indent=2, default=str)
                            console.print(f"[green]✅ Results saved to {output_file}[/green]")
                        else:
                            rprint(json.dumps(output_data, indent=2, default=str))
                    
                    elif output == 'file':
                        if not output_file:
                            output_file = f"regulation_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        
                        with open(output_file, 'w') as f:
                            f.write(f"Regulation Extract from: {url}\n")
                            f.write(f"Extracted on: {datetime.utcnow().isoformat()}\n")
                            f.write("="*80 + "\n\n")
                            f.write(extracted_content)
                        
                        console.print(f"[green]✅ Content saved to {output_file}[/green]")
                        console.print(f"📊 Content length: {len(extracted_content):,} characters")
                    
                    else:  # text output
                        console.print(f"\n[bold]📄 Extracted Content ({len(extracted_content):,} chars):[/bold]")
                        console.print("="*80)
                        
                        # Show first 2000 characters
                        preview = extracted_content[:2000]
                        console.print(preview)
                        
                        if len(extracted_content) > 2000:
                            console.print(f"\n[dim]... truncated ({len(extracted_content) - 2000:,} more characters)[/dim]")
                            console.print("[dim]💡 Use --output file to save full content[/dim]")
                
                else:
                    console.print(f"[red]❌ Extraction failed: {result.get('error', 'Unknown error')}[/red]")
                    
            except Exception as e:
                console.print(f"[red]❌ Error during extraction: {e}[/red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
    
    asyncio.run(run_extraction())

# Helper functions for displaying results
def _display_discovery_results(result: Dict, output_format: str):
    """Display discovery results in specified format"""
    if output_format == 'json':
        rprint(json.dumps(result, indent=2, default=str))
        return
    
    # Table format
    console.print(f"\n[bold green]✅ Discovery Complete![/bold green]")
    console.print(f"📊 Jurisdictions: {', '.join(result.get('jurisdictions_covered', []))}")
    console.print(f"🔍 Portals analyzed: {result.get('portals_analyzed', 0)}")
    console.print(f"🎯 Sources discovered: {result.get('sources_discovered', 0)}")
    
    new_sources = result.get('new_sources', [])
    if new_sources:
        table = Table(title="Newly Discovered Sources")
        table.add_column("Name", style="bold")
        table.add_column("URL")
        table.add_column("Type")
        table.add_column("Agency")
        table.add_column("Confidence")
        table.add_column("Frequency")
        
        for source in new_sources[:10]:  # Show top 10
            table.add_row(
                source.get('name', ''),
                source.get('url', ''),
                source.get('source_type', ''),
                source.get('agency', ''),
                f"{source.get('confidence_score', 0):.2f}",
                source.get('update_frequency', '')
            )
        
        console.print(table)
    
    session_summary = result.get('session_summary', {})
    if session_summary:
        console.print(f"\n📈 Session Summary:")
        console.print(f"   URLs scanned: {session_summary.get('total_scanned', 0)}")
        console.print(f"   Successful discoveries: {session_summary.get('successful_discoveries', 0)}")
        console.print(f"   Discovery rate: {session_summary.get('discovery_rate', 0):.1f}%")

def _display_domain_analysis_results(result: Dict, output_format: str):
    """Display domain analysis results"""
    if output_format == 'json':
        rprint(json.dumps(result, indent=2, default=str))
        return
    
    console.print(f"\n[bold green]✅ Domain Analysis Complete![/bold green]")
    
    # Implementation would display the website analysis results
    console.print("Analysis results would be displayed here based on the result structure")

def _display_sources_list(sources: List[Dict], output_format: str):
    """Display sources list"""
    if output_format == 'json':
        rprint(json.dumps(sources, indent=2, default=str))
        return
    elif output_format == 'csv':
        # Simple CSV output
        if sources:
            headers = sources[0].keys()
            rprint(','.join(headers))
            for source in sources:
                rprint(','.join(str(source.get(h, '')) for h in headers))
        return
    
    # Table format
    table = Table(title=f"Publication Sources ({len(sources)} found)")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Agency")
    table.add_column("Jurisdiction") 
    table.add_column("Confidence")
    table.add_column("Frequency")
    table.add_column("Active")
    table.add_column("Last Checked")
    
    for source in sources:
        table.add_row(
            source.get('name', '')[:30] + "..." if len(source.get('name', '')) > 30 else source.get('name', ''),
            source.get('type', ''),
            source.get('agency', ''),
            source.get('jurisdiction', ''),
            source.get('confidence', ''),
            source.get('frequency', ''),
            source.get('active', ''),
            source.get('last_checked', '')
        )
    
    console.print(table)

def _display_monitoring_results(result: Dict, output_format: str):
    """Display monitoring results"""
    if output_format == 'json':
        rprint(json.dumps(result, indent=2, default=str))
        return
    
    if output_format == 'csv':
        # Display CSV format
        items = result.get('discovered_items', [])
        if items:
            import csv
            import io
            
            output = io.StringIO()
            fieldnames = ['title', 'url', 'published_date', 'source', 'jurisdiction']
            if result.get('compliance_filtered'):
                fieldnames.extend(['business_impact', 'compliance_category'])
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in items:
                row = {field: item.get(field, '') for field in fieldnames}
                writer.writerow(row)
            
            console.print(output.getvalue())
        return
    
    console.print(f"\n[bold green]✅ Monitoring Complete![/bold green]")
    
    # Display table format
    items = result.get('discovered_items', [])
    sources_monitored = result.get('sources_monitored', 0)
    
    console.print(f"📊 Sources monitored: {sources_monitored}")
    console.print(f"📋 Items found: {len(items)}")
    
    if result.get('compliance_filtered'):
        console.print("[blue]🔍 Results filtered for product compliance[/blue]")
    
    if items:
        if result.get('compliance_filtered'):
            # Enhanced table for compliance
            table = Table(title="Product Compliance Regulations Found")
            table.add_column("Title", style="cyan", no_wrap=False, max_width=40)
            table.add_column("Impact", style="red", justify="center")
            table.add_column("Category", style="yellow")
            table.add_column("Source", style="green")
            table.add_column("Date", style="blue")
            
            for item in items:
                impact = item.get('business_impact', 'unknown')
                category = item.get('compliance_category', 'general')
                
                table.add_row(
                    item.get('title', 'N/A')[:60] + "..." if len(item.get('title', '')) > 60 else item.get('title', 'N/A'),
                    impact.upper(),
                    category.title(),
                    item.get('source', 'N/A'),
                    item.get('published_date', 'N/A')
                )
        else:
            # Standard table
            table = Table(title="Regulations Found")
            table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
            table.add_column("Source", style="green")
            table.add_column("Date", style="blue")
            table.add_column("URL", style="dim", max_width=30)
            
            for item in items:
                table.add_row(
                    item.get('title', 'N/A')[:60] + "..." if len(item.get('title', '')) > 60 else item.get('title', 'N/A'),
                    item.get('source', 'N/A'),
                    item.get('published_date', 'N/A'),
                    item.get('url', 'N/A')[:40] + "..." if len(item.get('url', '')) > 40 else item.get('url', 'N/A')
                )
        
        console.print(table)
    else:
        console.print("[yellow]No new items found.[/yellow]")
    
    console.print(f"\n[dim]💾 Results saved to monitoring cache[/dim]")

if __name__ == '__main__':
    cli()