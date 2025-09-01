#!/usr/bin/env python3
"""
Database Cleanup Script for Claude Regulation Scraper
Cleans up unused data files and keeps only actively used data
"""

import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import os

def cleanup_database():
    """Comprehensive database cleanup"""
    
    print("🧹 Starting Claude Regulation Scraper Database Cleanup...")
    total_freed = 0
    
    # Define active data directories
    user_storage = Path.home() / '.claude_regulation_scraper'
    project_dir = Path('.')
    
    # 1. Clean up old test results and temporary files
    print("\n📁 Cleaning up test results and temporary files...")
    
    test_dirs = [
        'daily_monitoring_reports',
        'daily_monitoring_test_results', 
        'monitoring_results',
        'test_results'
    ]
    
    for test_dir in test_dirs:
        test_path = project_dir / test_dir
        if test_path.exists():
            size = sum(f.stat().st_size for f in test_path.rglob('*') if f.is_file())
            total_freed += size
            shutil.rmtree(test_path)
            print(f"  ✅ Removed {test_dir} ({size/1024:.1f} KB)")
    
    # 2. Clean up old single test files
    print("\n📄 Cleaning up old test files...")
    
    test_patterns = [
        'publication_discovery_test_results_*.json',
        'test_*.json',
        '*_test_*.json',
        'workflow_test_*.json'
    ]
    
    for pattern in test_patterns:
        for file_path in project_dir.glob(pattern):
            size = file_path.stat().st_size
            total_freed += size
            file_path.unlink()
            print(f"  ✅ Removed {file_path.name} ({size/1024:.1f} KB)")
    
    # 3. Clean up duplicate data directories in project
    print("\n🗂️ Cleaning up duplicate data directories...")
    
    # Keep only the user storage, remove project duplicates
    duplicate_dirs = [
        'discovery_data',
        'feed_monitoring_data', 
        'monitoring_data',
        'intelligence_data'
    ]
    
    for dup_dir in duplicate_dirs:
        dup_path = project_dir / dup_dir
        if dup_path.exists():
            size = sum(f.stat().st_size for f in dup_path.rglob('*') if f.is_file())
            total_freed += size
            shutil.rmtree(dup_path)
            print(f"  ✅ Removed duplicate {dup_dir} ({size/1024:.1f} KB)")
    
    # 4. Clean up old learning data (keep only recent)
    print("\n🧠 Cleaning up old learning data...")
    
    learning_path = project_dir / 'learning_data'
    if learning_path.exists():
        # Clean up learning sessions older than 30 days
        sessions_file = learning_path / 'learning_sessions.json'
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
                
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                original_count = len(sessions)
                
                # Filter recent sessions
                recent_sessions = []
                for session in sessions:
                    try:
                        session_date = datetime.fromisoformat(session.get('timestamp', ''))
                        if session_date > cutoff_date:
                            recent_sessions.append(session)
                    except:
                        # Keep sessions with invalid dates for safety
                        recent_sessions.append(session)
                
                if len(recent_sessions) < original_count:
                    with open(sessions_file, 'w') as f:
                        json.dump(recent_sessions, f, indent=2)
                    print(f"  ✅ Cleaned learning sessions: {original_count} → {len(recent_sessions)}")
                
            except Exception as e:
                print(f"  ⚠️ Could not clean learning sessions: {e}")
    
    # 5. Clean up cache files in user storage
    print("\n💾 Cleaning up cache files...")
    
    if user_storage.exists():
        cache_files = [
            'data/seen_items_cache.json',
            'data/feed_cache.json',
            'data/temp_*.json'
        ]
        
        for cache_pattern in cache_files:
            for cache_file in user_storage.glob(cache_pattern):
                if cache_file.exists():
                    size = cache_file.stat().st_size
                    total_freed += size
                    cache_file.unlink()
                    print(f"  ✅ Removed cache {cache_file.name} ({size/1024:.1f} KB)")
    
    # 6. Clean up old monitoring data (keep only last 7 days)
    print("\n📊 Cleaning up old monitoring data...")
    
    monitoring_files = [
        user_storage / 'data' / 'feed_items.json',
        user_storage / 'data' / 'monitoring_sessions.json'
    ]
    
    for mon_file in monitoring_files:
        if mon_file.exists():
            try:
                with open(mon_file, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    cutoff_date = datetime.utcnow() - timedelta(days=7)
                    original_count = len(data)
                    
                    # Filter recent data
                    recent_data = []
                    for item in data:
                        try:
                            # Try different timestamp fields
                            timestamp_fields = ['timestamp', 'discovered_date', 'start_time', 'created_date']
                            item_date = None
                            
                            for field in timestamp_fields:
                                if field in item and item[field]:
                                    try:
                                        item_date = datetime.fromisoformat(str(item[field]))
                                        break
                                    except:
                                        continue
                            
                            if item_date and item_date > cutoff_date:
                                recent_data.append(item)
                            elif item_date is None:
                                # Keep items without valid dates for safety
                                recent_data.append(item)
                                
                        except:
                            # Keep items we can't parse for safety
                            recent_data.append(item)
                    
                    if len(recent_data) < original_count:
                        with open(mon_file, 'w') as f:
                            json.dump(recent_data, f, indent=2)
                        print(f"  ✅ Cleaned {mon_file.name}: {original_count} → {len(recent_data)} items")
                
            except Exception as e:
                print(f"  ⚠️ Could not clean {mon_file.name}: {e}")
    
    # 7. Verify active data integrity
    print("\n🔍 Verifying active data integrity...")
    
    active_files = [
        user_storage / 'data' / 'publication_sources.json',
        user_storage / 'data' / 'discovery_sessions.json',
        project_dir / 'learning_data' / 'jurisdiction_profiles.json'
    ]
    
    for active_file in active_files:
        if active_file.exists():
            try:
                with open(active_file, 'r') as f:
                    json.load(f)  # Just validate it's valid JSON
                print(f"  ✅ Verified {active_file.name}")
            except Exception as e:
                print(f"  ⚠️ Issue with {active_file.name}: {e}")
        else:
            print(f"  ℹ️ Missing {active_file.name} (will be created as needed)")
    
    # 8. Summary
    print(f"\n🎉 Cleanup Complete!")
    print(f"💾 Total space freed: {total_freed/1024:.1f} KB ({total_freed/1024/1024:.2f} MB)")
    
    # Show remaining data structure
    print(f"\n📋 Active data structure:")
    if user_storage.exists():
        print(f"  📁 User storage: {user_storage}")
        for file in sorted(user_storage.rglob('*.json')):
            size = file.stat().st_size
            print(f"    📄 {file.relative_to(user_storage)} ({size/1024:.1f} KB)")
    
    learning_path = project_dir / 'learning_data'
    if learning_path.exists():
        print(f"  📁 Learning data: {learning_path}")
        for file in sorted(learning_path.rglob('*.json')):
            size = file.stat().st_size
            print(f"    📄 {file.name} ({size/1024:.1f} KB)")
    
    print(f"\n✨ Database is now clean and optimized!")

if __name__ == "__main__":
    cleanup_database()