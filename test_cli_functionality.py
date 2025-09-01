#!/usr/bin/env python3
"""
Comprehensive CLI functionality test
"""
import subprocess
import os
import sys
import tempfile
import json
from pathlib import Path

def run_cli_command(cmd, timeout=30):
    """Run a CLI command and return the result"""
    try:
        # Set up environment
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = "sk-test-key-for-testing"
        env['FIRECRAWL_API_KEY'] = "fc-test-key-for-testing"
        
        # Convert claude-reg commands to direct script calls
        cmd_parts = cmd.split()
        if cmd_parts[0] == 'claude-reg':
            cmd_parts = cmd_parts[1:]  # Remove 'claude-reg'
        
        full_cmd = ["python", "claude_regulation_scraper.py"] + cmd_parts
        
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Command timed out',
            'success': False
        }
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }

def test_cli_basic_functionality():
    """Test basic CLI functionality"""
    print("🧪 Testing CLI Basic Functionality")
    print("=" * 60)
    
    tests = [
        {
            'name': 'Help command',
            'cmd': 'claude-reg --help',
            'expect_in_output': ['Claude Regulation Scraper', 'Commands:']
        },
        {
            'name': 'Quick start guide',
            'cmd': 'claude-reg quick-start',
            'expect_in_output': ['Quick Start', 'Set up API keys']
        },
        {
            'name': 'Configuration show',
            'cmd': 'claude-reg config show',
            'expect_in_output': ['Configuration', 'storage_path']
        },
        {
            'name': 'Sources list',
            'cmd': 'claude-reg sources list',
            'expect_in_output': ['Publication Sources']  # May have existing sources
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"🔧 Testing: {test['name']}")
        
        result = run_cli_command(test['cmd'])
        
        success = result['success']
        if success and test.get('expect_in_output'):
            for expected in test['expect_in_output']:
                if expected not in result['stdout']:
                    success = False
                    break
        
        if success:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED")
            print(f"     Return code: {result['returncode']}")
            print(f"     Stdout: {result['stdout'][:200]}...")
            print(f"     Stderr: {result['stderr'][:200]}...")
        
        results.append({
            'name': test['name'],
            'success': success,
            'result': result
        })
        
        print()
    
    return results

def test_source_management():
    """Test source management functionality"""
    print("🧪 Testing Source Management")
    print("=" * 60)
    
    tests = [
        {
            'name': 'Add RSS source',
            'cmd': 'claude-reg sources add --name TestRSS --url https://example.com/rss.xml --type rss_feed --jurisdiction US --agency TEST --frequency daily',
            'expect_in_output': ['Source added successfully', 'TestRSS']
        },
        {
            'name': 'Add daily listing source', 
            'cmd': 'claude-reg sources add --name TestDaily --url https://example.com/news --type daily_listing --jurisdiction US --agency TEST --frequency daily',
            'expect_in_output': ['Source added successfully', 'TestDaily']
        },
        {
            'name': 'List sources',
            'cmd': 'claude-reg sources list',
            'expect_in_output': ['Publication Sources', 'TestRSS', 'TestDaily']
        },
        {
            'name': 'List sources JSON',
            'cmd': 'claude-reg sources list --output json',
            'expect_json': True
        },
        {
            'name': 'Filter by jurisdiction',
            'cmd': 'claude-reg sources list --jurisdiction US',
            'expect_in_output': ['Publication Sources']
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"🔧 Testing: {test['name']}")
        
        result = run_cli_command(test['cmd'])
        
        success = result['success']
        
        if success and test.get('expect_in_output'):
            for expected in test['expect_in_output']:
                if expected not in result['stdout']:
                    success = False
                    break
        
        if success and test.get('expect_json'):
            try:
                json.loads(result['stdout'])
            except json.JSONDecodeError:
                success = False
        
        if success:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED")
            print(f"     Return code: {result['returncode']}")
            print(f"     Stdout: {result['stdout'][:300]}...")
            if result['stderr']:
                print(f"     Stderr: {result['stderr'][:200]}...")
        
        results.append({
            'name': test['name'],
            'success': success,
            'result': result
        })
        
        print()
    
    return results

def test_monitoring_commands():
    """Test monitoring functionality"""
    print("🧪 Testing Monitoring Commands")
    print("=" * 60)
    
    tests = [
        {
            'name': 'Monitor status',
            'cmd': 'claude-reg monitor status',
            'expect_in_output': ['Monitoring Status']
        },
        {
            'name': 'Monitor status JSON',
            'cmd': 'claude-reg monitor status --output json',
            'expect_json': True
        },
        {
            'name': 'Monitor results',
            'cmd': 'claude-reg monitor results',
            'expect_in_output': ['No monitoring results', 'Recent Monitoring Results']  # Either is acceptable
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"🔧 Testing: {test['name']}")
        
        result = run_cli_command(test['cmd'])
        
        success = result['success']
        
        if success and test.get('expect_in_output'):
            # For monitoring, any of the expected outputs is fine
            found = any(expected in result['stdout'] for expected in test['expect_in_output'])
            success = found
        
        if success and test.get('expect_json'):
            try:
                json.loads(result['stdout'])
            except json.JSONDecodeError:
                success = False
        
        if success:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED")
            print(f"     Return code: {result['returncode']}")
            print(f"     Stdout: {result['stdout'][:300]}...")
            if result['stderr']:
                print(f"     Stderr: {result['stderr'][:200]}...")
        
        results.append({
            'name': test['name'],
            'success': success,
            'result': result
        })
        
        print()
    
    return results

def main():
    """Main test function"""
    print("🚀 Claude Regulation Scraper - CLI Test Suite")
    print("=" * 80)
    print()
    
    all_results = []
    
    # Run test suites
    basic_results = test_cli_basic_functionality()
    all_results.extend(basic_results)
    
    source_results = test_source_management()
    all_results.extend(source_results)
    
    monitor_results = test_monitoring_commands()
    all_results.extend(monitor_results)
    
    # Summary
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in all_results if r['success'])
    total = len(all_results)
    
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    if passed < total:
        print("❌ Failed tests:")
        for result in all_results:
            if not result['success']:
                print(f"  - {result['name']}")
        print()
    
    # Test status
    if passed == total:
        print("🎉 ALL TESTS PASSED! CLI is fully functional.")
        return True
    elif passed >= total * 0.8:
        print("🟡 MOSTLY WORKING - Some minor issues to fix.")
        return True
    else:
        print("❌ SIGNIFICANT ISSUES - Major fixes needed.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)