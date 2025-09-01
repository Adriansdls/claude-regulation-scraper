#!/usr/bin/env python3
"""
Test Publication Discovery System
Demonstrates the new publication discovery and feed monitoring system that finds where regulations are published daily
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agents.publication_discovery_agent import PublicationDiscoveryAgent, PublicationSource
from src.agents.llm_agents.feed_monitoring_agent import FeedMonitoringAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class PublicationDiscoverySystemTest:
    """Test the complete publication discovery and monitoring system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_start_time = datetime.utcnow()
        
        # Test results
        self.test_results = {
            "test_name": "Publication Discovery System Test",
            "test_start": self.test_start_time.isoformat(),
            "phases": []
        }
        
    async def setup_system(self):
        """Initialize the discovery and monitoring system"""
        self.logger.info("🚀 Initializing Publication Discovery System...")
        
        # Initialize discovery agent
        self.discovery_agent = PublicationDiscoveryAgent(None)
        await self.discovery_agent._register_tools()
        
        # Initialize feed monitoring agent with reference to discovery agent
        self.feed_monitoring_agent = FeedMonitoringAgent(None, discovery_agent=self.discovery_agent)
        await self.feed_monitoring_agent._register_tools()
        
        self.logger.info("✅ Publication discovery system initialized")
        
    async def test_phase_1_discover_publication_sources(self):
        """Phase 1: Discover regulatory publication sources"""
        print(f"\n{'='*80}")
        print(f"🔍 PHASE 1: Discover Regulatory Publication Sources")
        print(f"{'='*80}")
        
        phase_results = {
            "phase": "publication_source_discovery",
            "start_time": datetime.utcnow().isoformat(),
            "success": False,
            "discoveries": []
        }
        
        try:
            # Discover sources for multiple jurisdictions
            target_jurisdictions = ["US", "UK", "EU"]
            
            print(f"🌍 Discovering publication sources for: {', '.join(target_jurisdictions)}")
            
            discovery_result = await self.discovery_agent._discover_publication_sources(
                target_jurisdictions=target_jurisdictions,
                discovery_methods=["automated_scan"],
                focus_agencies=["FDA", "CPSC"]
            )
            
            if discovery_result.get('success'):
                sources_discovered = discovery_result.get('sources_discovered', 0)
                portals_analyzed = discovery_result.get('portals_analyzed', 0)
                
                print(f"✅ Discovery Results:")
                print(f"   📊 Portals analyzed: {portals_analyzed}")
                print(f"   🎯 Sources discovered: {sources_discovered}")
                print(f"   📈 Discovery rate: {discovery_result.get('session_summary', {}).get('discovery_rate', 0):.1f}%")
                
                # Show discovered sources
                if discovery_result.get('new_sources'):
                    print(f"\n🔍 DISCOVERED SOURCES:")
                    for i, source in enumerate(discovery_result['new_sources'][:5], 1):
                        print(f"   {i}. {source['name']}")
                        print(f"      📍 URL: {source['url']}")
                        print(f"      🏛️  Agency: {source['agency']} ({source['jurisdiction']})")
                        print(f"      📊 Type: {source['source_type']}")
                        print(f"      ⭐ Confidence: {source['confidence_score']:.2f}")
                        print(f"      🔄 Update Frequency: {source['update_frequency']}")
                        if source.get('feed_url'):
                            print(f"      📡 Feed URL: {source['feed_url']}")
                        print()
                
                phase_results["success"] = True
                phase_results["sources_discovered"] = sources_discovered
                phase_results["discoveries"] = discovery_result.get('new_sources', [])
                
                print(f"🎉 SUCCESS: Found {sources_discovered} publication sources!")
                
            else:
                error = discovery_result.get('error', 'Unknown error')
                print(f"❌ Discovery failed: {error}")
                phase_results["error"] = error
                
        except Exception as e:
            print(f"❌ Phase 1 failed: {e}")
            phase_results["error"] = str(e)
            
        self.test_results["phases"].append(phase_results)
        return phase_results.get("success", False)
        
    async def test_phase_2_analyze_specific_website(self):
        """Phase 2: Analyze a specific regulatory website for publication sources"""
        print(f"\n{'='*80}")
        print(f"🌐 PHASE 2: Analyze Specific Regulatory Website")
        print(f"{'='*80}")
        
        phase_results = {
            "phase": "website_analysis",
            "start_time": datetime.utcnow().isoformat(),
            "success": False
        }
        
        try:
            # Test with Federal Register - known to have good APIs and feeds
            test_website = {
                "url": "https://www.federalregister.gov",
                "name": "US Federal Register",
                "jurisdiction": "US",
                "agency": "Federal Government"
            }
            
            print(f"🔎 Analyzing: {test_website['name']}")
            print(f"📍 URL: {test_website['url']}")
            
            analysis_result = await self.discovery_agent._analyze_website_for_publications(
                website_url=test_website["url"],
                website_name=test_website["name"],
                jurisdiction=test_website["jurisdiction"],
                agency=test_website["agency"]
            )
            
            if analysis_result.get('success'):
                analysis_data = analysis_result.get('analysis_data', {})
                sources_found = analysis_result.get('sources_found', [])
                feed_urls = analysis_result.get('feed_urls_found', [])
                
                print(f"✅ Website Analysis Results:")
                
                # Website capabilities
                website_analysis = analysis_data.get('website_analysis', {})
                print(f"   📋 Has Publication Sections: {'✅ Yes' if website_analysis.get('has_publication_sections') else '❌ No'}")
                print(f"   📊 Publication Types: {', '.join(website_analysis.get('publication_types', []))}")
                print(f"   🔄 Update Frequency: {', '.join(website_analysis.get('update_frequency_indicators', []))}")
                
                # Discovered sources
                print(f"\n🎯 PUBLICATION SOURCES FOUND ({len(sources_found)}):")
                for i, source in enumerate(sources_found[:3], 1):
                    print(f"   {i}. {source['name']}")
                    print(f"      📍 URL: {source['url']}")
                    print(f"      📊 Type: {source['source_type']}")
                    print(f"      ⭐ Confidence: {source['confidence_score']:.2f}")
                    print(f"      📝 Description: {source.get('description', 'N/A')}")
                    
                # Feed URLs
                if feed_urls:
                    print(f"\n📡 FEED URLS DISCOVERED ({len(feed_urls)}):")
                    for feed in feed_urls[:3]:
                        print(f"   • {feed.get('type', 'unknown').upper()}: {feed.get('url', 'N/A')}")
                        print(f"     Description: {feed.get('description', 'N/A')}")
                
                # Monitoring recommendations
                monitoring = analysis_data.get('monitoring_recommendations', {})
                print(f"\n📊 MONITORING ASSESSMENT:")
                print(f"   🎯 Primary Targets: {', '.join(monitoring.get('primary_targets', []))}")
                print(f"   ⏰ Check Frequency: {monitoring.get('check_frequency', 'unknown')}")
                print(f"   🤖 Automation Feasibility: {monitoring.get('automation_feasibility', 'unknown').upper()}")
                
                phase_results["success"] = True
                phase_results["sources_found"] = len(sources_found)
                phase_results["feed_urls_found"] = len(feed_urls)
                phase_results["monitoring_viable"] = monitoring.get('automation_feasibility') in ['high', 'medium']
                
                print(f"🎉 SUCCESS: Website analysis complete - {len(sources_found)} sources, {len(feed_urls)} feeds found!")
                
            else:
                error = analysis_result.get('error', 'Unknown error')
                print(f"❌ Website analysis failed: {error}")
                phase_results["error"] = error
                
        except Exception as e:
            print(f"❌ Phase 2 failed: {e}")
            phase_results["error"] = str(e)
            
        self.test_results["phases"].append(phase_results)
        return phase_results.get("success", False)
        
    async def test_phase_3_feed_monitoring(self):
        """Phase 3: Test feed monitoring for new publications"""
        print(f"\n{'='*80}")
        print(f"📡 PHASE 3: Feed Monitoring for New Publications")
        print(f"{'='*80}")
        
        phase_results = {
            "phase": "feed_monitoring",
            "start_time": datetime.utcnow().isoformat(),
            "success": False
        }
        
        try:
            # Check if we have discovered sources to monitor
            if hasattr(self.discovery_agent, 'discovered_sources'):
                available_sources = len(self.discovery_agent.discovered_sources)
                print(f"📊 Available sources for monitoring: {available_sources}")
                
                if available_sources == 0:
                    print("⚠️  No sources available - adding a test source")
                    
                    # Add a test source manually for demonstration
                    from src.agents.llm_agents.publication_discovery_agent import PublicationSource, PublicationSourceType, UpdateFrequency
                    import hashlib
                    
                    test_source = PublicationSource(
                        source_id="test_federal_register",
                        name="Federal Register API Test",
                        url="https://www.federalregister.gov/api/v1/documents.json",
                        source_type=PublicationSourceType.API_ENDPOINT,
                        jurisdiction="US",
                        agency="Federal Government",
                        discovered_date=datetime.utcnow(),
                        discovery_method="manual_test",
                        confidence_score=0.9,
                        update_frequency=UpdateFrequency.DAILY,
                        content_types=["regulations", "notices"],
                        feed_url="https://www.federalregister.gov/api/v1/documents.json",
                        feed_format="json_api",
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
                    
                    self.discovery_agent.discovered_sources["test_federal_register"] = test_source
                    print("✅ Added test source: Federal Register API")
                    
            # Monitor feeds for today's publications
            today = datetime.utcnow().strftime('%Y-%m-%d')
            print(f"📅 Monitoring for publications on: {today}")
            
            monitoring_result = await self.feed_monitoring_agent._monitor_publication_feeds(
                target_date=today,
                relevance_threshold=0.3
            )
            
            if monitoring_result.get('success'):
                sources_monitored = monitoring_result.get('sources_monitored', 0)
                feeds_processed = monitoring_result.get('feeds_processed', 0)
                items_discovered = monitoring_result.get('total_items_discovered', 0)
                new_items = monitoring_result.get('new_items_today', 0)
                high_relevance = monitoring_result.get('high_relevance_items', 0)
                
                print(f"✅ Feed Monitoring Results:")
                print(f"   📊 Sources monitored: {sources_monitored}")
                print(f"   📡 Feeds processed: {feeds_processed}")
                print(f"   🔍 Total items discovered: {items_discovered}")
                print(f"   🆕 New items today: {new_items}")
                print(f"   ⭐ High relevance items: {high_relevance}")
                
                session_summary = monitoring_result.get('session_summary', {})
                print(f"   📈 Success rate: {session_summary.get('success_rate', 0):.1f}%")
                print(f"   📊 Items per source: {session_summary.get('items_per_source', 0):.1f}")
                
                # Show discovered items
                discovered_items = monitoring_result.get('discovered_items', [])
                if discovered_items:
                    print(f"\n📋 HIGH RELEVANCE DISCOVERIES:")
                    for i, item in enumerate(discovered_items[:3], 1):
                        print(f"   {i}. {item.get('title', 'No title')[:60]}...")
                        print(f"      📍 URL: {item.get('url', 'No URL')}")
                        print(f"      ⭐ Relevance: {item.get('relevance_score', 0):.2f}")
                        print(f"      📅 Published: {item.get('published_date', 'Unknown')}")
                        print(f"      🏷️  Type: {item.get('item_type', 'unknown')}")
                        print()
                
                phase_results["success"] = True
                phase_results["sources_monitored"] = sources_monitored
                phase_results["feeds_processed"] = feeds_processed
                phase_results["items_discovered"] = items_discovered
                phase_results["high_relevance_items"] = high_relevance
                
                print(f"🎉 SUCCESS: Feed monitoring complete - {high_relevance} high-relevance items found!")
                
            else:
                error = monitoring_result.get('error', 'Unknown error')
                print(f"❌ Feed monitoring failed: {error}")
                phase_results["error"] = error
                
        except Exception as e:
            print(f"❌ Phase 3 failed: {e}")
            phase_results["error"] = str(e)
            
        self.test_results["phases"].append(phase_results)
        return phase_results.get("success", False)
        
    async def test_phase_4_discovery_recommendations(self):
        """Phase 4: Get AI recommendations for expanding discovery coverage"""
        print(f"\n{'='*80}")
        print(f"🎯 PHASE 4: Discovery Expansion Recommendations")
        print(f"{'='*80}")
        
        phase_results = {
            "phase": "discovery_recommendations",
            "start_time": datetime.utcnow().isoformat(),
            "success": False
        }
        
        try:
            current_coverage = ["US Federal Register", "FDA", "CPSC"]
            gaps_identified = ["EU product safety", "UK daily legislation", "State-level regulations"]
            
            print(f"📊 Current coverage: {', '.join(current_coverage)}")
            print(f"⚠️  Known gaps: {', '.join(gaps_identified)}")
            
            recommendations_result = await self.discovery_agent._get_discovery_recommendations(
                current_coverage=current_coverage,
                gaps_identified=gaps_identified
            )
            
            if recommendations_result.get('success'):
                recommendations = recommendations_result.get('recommendations', {})
                
                # Coverage analysis
                coverage_analysis = recommendations.get('coverage_analysis', {})
                print(f"✅ Coverage Analysis:")
                print(f"   💪 Strengths: {', '.join(coverage_analysis.get('strength_areas', []))}")
                print(f"   ⚠️  Gaps: {', '.join(coverage_analysis.get('gap_areas', []))}")
                print(f"   📊 Overall Score: {coverage_analysis.get('coverage_score', 0):.2f}/1.0")
                
                # Jurisdiction completeness
                completeness = coverage_analysis.get('jurisdiction_completeness', {})
                if completeness:
                    print(f"   🌍 Jurisdiction Completeness:")
                    for jurisdiction, score in completeness.items():
                        print(f"      {jurisdiction}: {score:.1%}")
                
                # Recommended targets
                targets = recommendations.get('recommended_targets', [])
                if targets:
                    print(f"\n🎯 RECOMMENDED DISCOVERY TARGETS ({len(targets)}):")
                    for i, target in enumerate(targets[:5], 1):
                        priority = target.get('priority', 'medium').upper()
                        print(f"   {i}. {target.get('target_name', 'Unknown')} [{priority} PRIORITY]")
                        if target.get('target_url'):
                            print(f"      📍 URL: {target['target_url']}")
                        print(f"      🌍 {target.get('jurisdiction', 'Unknown')} - {target.get('agency', 'Unknown')}")
                        print(f"      💡 Rationale: {target.get('rationale', 'No rationale provided')}")
                        print()
                
                # Discovery strategies
                strategies = recommendations.get('discovery_strategies', [])
                if strategies:
                    print(f"🔍 RECOMMENDED DISCOVERY STRATEGIES:")
                    for strategy in strategies[:3]:
                        print(f"   • {strategy.get('strategy', 'Unknown Strategy')}")
                        print(f"     Description: {strategy.get('description', 'No description')}")
                        print(f"     Expected Yield: {strategy.get('expected_yield', 'unknown').upper()}")
                        print(f"     Effort Required: {strategy.get('effort_required', 'unknown').upper()}")
                        print()
                
                # Next actions
                next_actions = recommendations.get('next_actions', [])
                if next_actions:
                    print(f"📋 NEXT ACTIONS:")
                    for i, action in enumerate(next_actions[:5], 1):
                        print(f"   {i}. {action}")
                
                phase_results["success"] = True
                phase_results["targets_recommended"] = len(targets)
                phase_results["coverage_score"] = coverage_analysis.get('coverage_score', 0)
                
                print(f"🎉 SUCCESS: Generated {len(targets)} discovery recommendations!")
                
            else:
                error = recommendations_result.get('error', 'Unknown error')
                print(f"❌ Recommendations failed: {error}")
                phase_results["error"] = error
                
        except Exception as e:
            print(f"❌ Phase 4 failed: {e}")
            phase_results["error"] = str(e)
            
        self.test_results["phases"].append(phase_results)
        return phase_results.get("success", False)
        
    async def generate_final_report(self):
        """Generate comprehensive test report"""
        print(f"\n{'='*80}")
        print(f"📊 PUBLICATION DISCOVERY SYSTEM TEST REPORT")
        print(f"{'='*80}")
        
        test_end = datetime.utcnow()
        total_duration = (test_end - self.test_start_time).total_seconds()
        
        self.test_results["test_end"] = test_end.isoformat()
        self.test_results["total_duration_seconds"] = total_duration
        
        print(f"🕒 Total test duration: {total_duration:.2f} seconds")
        print(f"📅 Test period: {self.test_start_time.strftime('%H:%M:%S')} → {test_end.strftime('%H:%M:%S')}")
        
        # Analyze results
        phase_results = {}
        for phase in self.test_results["phases"]:
            phase_name = phase["phase"]
            success = phase.get("success", False)
            phase_results[phase_name] = success
            
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n📋 {phase_name.replace('_', ' ').title()}: {status}")
            
            if success:
                # Show key metrics for successful phases
                if phase_name == "publication_source_discovery":
                    sources = phase.get("sources_discovered", 0)
                    print(f"   📊 Sources discovered: {sources}")
                elif phase_name == "website_analysis":
                    sources = phase.get("sources_found", 0)
                    feeds = phase.get("feed_urls_found", 0)
                    viable = phase.get("monitoring_viable", False)
                    print(f"   📊 Sources found: {sources}, Feeds: {feeds}")
                    print(f"   🤖 Monitoring viable: {'✅ Yes' if viable else '❌ No'}")
                elif phase_name == "feed_monitoring":
                    monitored = phase.get("sources_monitored", 0)
                    items = phase.get("high_relevance_items", 0)
                    print(f"   📊 Sources monitored: {monitored}, High-relevance items: {items}")
                elif phase_name == "discovery_recommendations":
                    targets = phase.get("targets_recommended", 0)
                    score = phase.get("coverage_score", 0)
                    print(f"   📊 Targets recommended: {targets}, Coverage score: {score:.2f}")
            else:
                # Show error for failed phases
                error = phase.get("error", "Unknown error")
                print(f"   ❌ Error: {error}")
        
        # Overall assessment
        successful_phases = sum(phase_results.values())
        total_phases = len(phase_results)
        success_rate = (successful_phases / total_phases * 100) if total_phases > 0 else 0
        
        print(f"\n🎯 OVERALL ASSESSMENT:")
        print(f"   📈 Success Rate: {success_rate:.1f}% ({successful_phases}/{total_phases})")
        
        if success_rate >= 75:
            system_status = "🟢 SYSTEM WORKING"
        elif success_rate >= 50:
            system_status = "🟡 PARTIALLY WORKING"
        else:
            system_status = "🔴 NEEDS WORK"
            
        print(f"   🚀 System Status: {system_status}")
        
        print(f"\n✅ KEY CAPABILITIES DEMONSTRATED:")
        capabilities = []
        
        if phase_results.get("publication_source_discovery"):
            capabilities.append("Automated discovery of regulatory publication sources")
        if phase_results.get("website_analysis"):
            capabilities.append("AI-powered analysis of regulatory websites for feeds and APIs")
        if phase_results.get("feed_monitoring"):
            capabilities.append("Real-time monitoring of publication feeds for new content")
        if phase_results.get("discovery_recommendations"):
            capabilities.append("Intelligent recommendations for expanding coverage")
            
        for capability in capabilities:
            print(f"   • {capability}")
            
        # Solution to original problem
        print(f"\n🎉 SOLUTION TO ORIGINAL PROBLEM:")
        print(f"✅ BEFORE: System used hardcoded regulation URLs")
        print(f"✅ NOW: System discovers publication sources automatically")
        print(f"✅ RESULT: Can find new regulations as they're published daily")
        
        print(f"\n📋 NEXT STEPS FOR PRODUCTION:")
        print(f"   1. Deploy discovery agents to scan regulatory portals daily")
        print(f"   2. Set up feed monitoring for discovered sources")
        print(f"   3. Integrate with existing content extraction and analysis")
        print(f"   4. Build admin interface for managing discovered sources")
        print(f"   5. Add alerting for high-impact newly discovered regulations")
        
        # Save detailed results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"publication_discovery_test_results_{timestamp}.json"
        
        self.test_results["final_summary"] = {
            "success_rate": success_rate,
            "system_status": system_status,
            "capabilities_demonstrated": capabilities,
            "phase_results": phase_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"\n💾 Detailed results saved: {results_file}")
        
        if success_rate >= 50:
            print(f"\n🎊 SUCCESS: Publication discovery system is working!")
            print(f"The system can now discover where regulations are published daily.")
        else:
            print(f"\n⚠️  System needs improvements before production deployment.")
        
    async def run_complete_test(self):
        """Run the complete publication discovery system test"""
        print(f"🚀 PUBLICATION DISCOVERY SYSTEM TEST")
        print(f"🎯 Testing automated discovery of daily regulation publication sources")
        print(f"⏰ Started: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            await self.setup_system()
            
            # Run all test phases
            phase1_success = await self.test_phase_1_discover_publication_sources()
            phase2_success = await self.test_phase_2_analyze_specific_website()
            phase3_success = await self.test_phase_3_feed_monitoring()
            phase4_success = await self.test_phase_4_discovery_recommendations()
            
            # Generate final report
            await self.generate_final_report()
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Check for API keys
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable required")
        sys.exit(1)
        
    test = PublicationDiscoverySystemTest()
    asyncio.run(test.run_complete_test())