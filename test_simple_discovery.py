#!/usr/bin/env python3
"""
Simple test to verify the publication discovery agent method fix
"""
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.llm_agents.publication_discovery_agent import PublicationDiscoveryAgent
from src.infrastructure.message_broker import MessageBroker, MessageType
from src.agents.llm_agents.base_agent import AgentRole

async def test_simple_generation():
    """Test that the generate_response method works"""
    print("🧪 Testing simple LLM generation...")
    
    try:
        # Initialize message broker
        broker = MessageBroker()
        
        # Create agent
        agent = PublicationDiscoveryAgent(
            broker=broker,
            storage_path="./test_discovery_data"
        )
        
        # Test generate_response method directly
        test_prompt = "List three major regulatory agencies in the United States."
        
        print(f"🤖 Asking: {test_prompt}")
        
        response = await agent.generate_response(test_prompt)
        
        print(f"✅ Response received:")
        print(f"   Content: {response.get('content', 'No content')[:200]}...")
        print(f"   Token usage: {response.get('token_usage', {})}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Simple Publication Discovery Agent Test")
    print("="*60)
    
    success = await test_simple_generation()
    
    if success:
        print("\n🎉 SUCCESS: Agent method fixes are working!")
    else:
        print("\n❌ FAILURE: Agent still has issues")
    
    return success

if __name__ == "__main__":
    # Set up environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable required")
        sys.exit(1)
    
    # Run test
    result = asyncio.run(main())
    sys.exit(0 if result else 1)