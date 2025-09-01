"""
SDK Agent Factory
Factory for creating and coordinating OpenAI Agents SDK-based agents
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .sdk_base_agent import BaseSDKAgent
from .sdk_discovery_agent import SDKDiscoveryAgent
from .sdk_orchestrator_agent import SDKOrchestratorAgent
from .sdk_html_agent import SDKHTMLExtractionAgent
from ...infrastructure.message_broker import MessageBroker
from ...config.config_manager import get_config


@dataclass
class SDKAgentRegistry:
    """Registry of SDK-based agents"""
    discovery_agent: Optional[SDKDiscoveryAgent] = None
    orchestrator_agent: Optional[SDKOrchestratorAgent] = None
    html_extraction_agent: Optional[SDKHTMLExtractionAgent] = None
    # pdf_analysis_agent: Optional[SDKPDFAnalysisAgent] = None  # To be implemented
    # vision_processing_agent: Optional[SDKVisionProcessingAgent] = None  # To be implemented
    # content_validation_agent: Optional[SDKContentValidationAgent] = None  # To be implemented


class SDKAgentFactory:
    """Factory for creating and managing SDK-based agents"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.registry = SDKAgentRegistry()
        
    async def create_all_agents(self) -> SDKAgentRegistry:
        """Create all SDK-based agents with proper dependencies"""
        try:
            self.logger.info("Creating SDK-based agent ecosystem")
            
            # Create individual agents first
            await self._create_discovery_agent()
            await self._create_html_extraction_agent()
            # await self._create_pdf_analysis_agent()  # To be implemented
            # await self._create_vision_processing_agent()  # To be implemented
            # await self._create_content_validation_agent()  # To be implemented
            
            # Create orchestrator with references to other agents
            await self._create_orchestrator_agent()
            
            self.logger.info("SDK agent ecosystem created successfully")
            return self.registry
            
        except Exception as e:
            self.logger.error(f"Failed to create SDK agent ecosystem: {e}")
            raise
    
    async def _create_discovery_agent(self):
        """Create SDK Discovery Agent"""
        try:
            self.registry.discovery_agent = SDKDiscoveryAgent(self.broker)
            self.logger.info("Created SDK Discovery Agent")
        except Exception as e:
            self.logger.error(f"Failed to create Discovery Agent: {e}")
            raise
    
    async def _create_html_extraction_agent(self):
        """Create SDK HTML Extraction Agent"""
        try:
            self.registry.html_extraction_agent = SDKHTMLExtractionAgent(self.broker)
            self.logger.info("Created SDK HTML Extraction Agent")
        except Exception as e:
            self.logger.error(f"Failed to create HTML Extraction Agent: {e}")
            raise
    
    async def _create_orchestrator_agent(self):
        """Create SDK Orchestrator Agent with handoff capabilities"""
        try:
            self.registry.orchestrator_agent = SDKOrchestratorAgent(
                broker=self.broker,
                discovery_agent=self.registry.discovery_agent.sdk_agent if self.registry.discovery_agent else None,
                html_agent=self.registry.html_extraction_agent.sdk_agent if self.registry.html_extraction_agent else None,
                # pdf_agent=self.registry.pdf_analysis_agent.sdk_agent if self.registry.pdf_analysis_agent else None,
                # vision_agent=self.registry.vision_processing_agent.sdk_agent if self.registry.vision_processing_agent else None,
                # validator_agent=self.registry.content_validation_agent.sdk_agent if self.registry.content_validation_agent else None
            )
            self.logger.info("Created SDK Orchestrator Agent with handoff capabilities")
        except Exception as e:
            self.logger.error(f"Failed to create Orchestrator Agent: {e}")
            raise
    
    async def start_all_agents(self) -> bool:
        """Start all SDK-based agents"""
        try:
            self.logger.info("Starting all SDK-based agents")
            
            # Start agents in dependency order
            agents_to_start = [
                ("Discovery", self.registry.discovery_agent),
                ("HTML Extraction", self.registry.html_extraction_agent),
                # ("PDF Analysis", self.registry.pdf_analysis_agent),
                # ("Vision Processing", self.registry.vision_processing_agent),
                # ("Content Validation", self.registry.content_validation_agent),
                ("Orchestrator", self.registry.orchestrator_agent)  # Start orchestrator last
            ]
            
            for name, agent in agents_to_start:
                if agent:
                    try:
                        await agent.start()
                        self.logger.info(f"Started {name} Agent")
                    except Exception as e:
                        self.logger.error(f"Failed to start {name} Agent: {e}")
                        return False
            
            self.logger.info("All SDK-based agents started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start SDK agents: {e}")
            return False
    
    async def stop_all_agents(self):
        """Stop all SDK-based agents"""
        try:
            self.logger.info("Stopping all SDK-based agents")
            
            # Stop agents in reverse dependency order
            agents_to_stop = [
                ("Orchestrator", self.registry.orchestrator_agent),
                # ("Content Validation", self.registry.content_validation_agent),
                # ("Vision Processing", self.registry.vision_processing_agent),
                # ("PDF Analysis", self.registry.pdf_analysis_agent),
                ("HTML Extraction", self.registry.html_extraction_agent),
                ("Discovery", self.registry.discovery_agent)
            ]
            
            for name, agent in agents_to_stop:
                if agent:
                    try:
                        await agent.stop()
                        self.logger.info(f"Stopped {name} Agent")
                    except Exception as e:
                        self.logger.warning(f"Error stopping {name} Agent: {e}")
            
            self.logger.info("All SDK-based agents stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping SDK agents: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            "discovery_agent": None,
            "orchestrator_agent": None,
            "html_extraction_agent": None,
            "total_active": 0,
            "ecosystem_health": "unknown"
        }
        
        active_count = 0
        
        if self.registry.discovery_agent:
            status["discovery_agent"] = self.registry.discovery_agent.get_metrics()
            if status["discovery_agent"]["status"] == "ready":
                active_count += 1
        
        if self.registry.orchestrator_agent:
            status["orchestrator_agent"] = self.registry.orchestrator_agent.get_metrics()
            if status["orchestrator_agent"]["status"] == "ready":
                active_count += 1
        
        if self.registry.html_extraction_agent:
            status["html_extraction_agent"] = self.registry.html_extraction_agent.get_metrics()
            if status["html_extraction_agent"]["status"] == "ready":
                active_count += 1
        
        status["total_active"] = active_count
        
        # Determine overall health
        total_agents = sum(1 for agent in [
            self.registry.discovery_agent,
            self.registry.orchestrator_agent, 
            self.registry.html_extraction_agent
        ] if agent is not None)
        
        if active_count == total_agents and total_agents > 0:
            status["ecosystem_health"] = "healthy"
        elif active_count > 0:
            status["ecosystem_health"] = "partial"
        else:
            status["ecosystem_health"] = "down"
        
        return status


async def create_sdk_agent_ecosystem(broker: MessageBroker) -> SDKAgentRegistry:
    """Create complete SDK-based agent ecosystem"""
    factory = SDKAgentFactory(broker)
    registry = await factory.create_all_agents()
    
    # Start all agents
    success = await factory.start_all_agents()
    if not success:
        await factory.stop_all_agents()
        raise RuntimeError("Failed to start SDK agent ecosystem")
    
    return registry


# Example usage and testing functions
async def test_sdk_agent_workflow():
    """Test the complete SDK agent workflow"""
    from ...infrastructure.message_broker import create_memory_broker
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create message broker
        broker = create_memory_broker()
        
        # Create agent ecosystem
        logger.info("Creating SDK agent ecosystem for testing")
        registry = await create_sdk_agent_ecosystem(broker)
        
        # Test orchestration workflow
        logger.info("Testing orchestration workflow")
        
        # Simulate a regulation extraction request
        test_message = {
            "job_id": "test_sdk_job_001",
            "url": "https://www.legislation.gov.uk/ukpga/2023/1",
            "requirements": {
                "priority": "high",
                "document_types": ["act", "regulation"],
                "max_documents": 50,
                "validation_required": True
            }
        }
        
        # Send test job to orchestrator
        from ...infrastructure.message_broker import create_message, MessageType
        message = await create_message(
            message_type=MessageType.JOB_CREATED,
            sender="test_client",
            recipient="orchestrator",
            payload=test_message,
            correlation_id="test_correlation_001"
        )
        
        await broker.publish(message)
        
        # Wait for processing
        logger.info("Waiting for workflow completion...")
        await asyncio.sleep(10)  # Allow time for processing
        
        # Get agent status
        factory = SDKAgentFactory(broker)
        factory.registry = registry
        status = factory.get_agent_status()
        
        logger.info(f"Agent ecosystem status: {status}")
        
        # Cleanup
        await factory.stop_all_agents()
        
        logger.info("SDK agent workflow test completed")
        return True
        
    except Exception as e:
        logger.error(f"SDK agent workflow test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test workflow
    import logging
    logging.basicConfig(level=logging.INFO)
    
    result = asyncio.run(test_sdk_agent_workflow())
    print(f"Test result: {'PASSED' if result else 'FAILED'}")