#!/usr/bin/env python3
"""
Learning Data Reset Tool
Provides CLI commands to reset various parts of the learning system for testing
"""

import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil

def reset_learning_sessions(learning_data_dir: str = "./learning_data"):
    """Reset all learning sessions"""
    sessions_file = Path(learning_data_dir) / "learning_sessions.json"
    
    if sessions_file.exists():
        # Backup first
        backup_file = sessions_file.with_suffix(f".json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(sessions_file, backup_file)
        print(f"📁 Backed up learning sessions to: {backup_file}")
    
    # Reset to empty array
    with open(sessions_file, 'w') as f:
        json.dump([], f, indent=2)
    
    print("🗑️  Learning sessions reset to empty")

def reset_jurisdiction_profiles(learning_data_dir: str = "./learning_data"):
    """Reset all jurisdiction profiles"""
    profiles_file = Path(learning_data_dir) / "jurisdiction_profiles.json"
    
    if profiles_file.exists():
        # Backup first
        backup_file = profiles_file.with_suffix(f".json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(profiles_file, backup_file)
        print(f"📁 Backed up jurisdiction profiles to: {backup_file}")
    
    # Reset to empty object
    with open(profiles_file, 'w') as f:
        json.dump({}, f, indent=2)
    
    print("🗑️  Jurisdiction profiles reset to empty")

def reset_specific_jurisdiction(jurisdiction: str, learning_data_dir: str = "./learning_data"):
    """Reset data for a specific jurisdiction"""
    profiles_file = Path(learning_data_dir) / "jurisdiction_profiles.json"
    sessions_file = Path(learning_data_dir) / "learning_sessions.json"
    
    # Reset jurisdiction profile
    if profiles_file.exists():
        with open(profiles_file, 'r') as f:
            data = json.load(f)
        
        if jurisdiction in data:
            del data[jurisdiction]
            
            with open(profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"🗑️  Removed jurisdiction '{jurisdiction}' from profiles")
        else:
            print(f"ℹ️  Jurisdiction '{jurisdiction}' not found in profiles")
    
    # Remove sessions for this jurisdiction
    if sessions_file.exists():
        with open(sessions_file, 'r') as f:
            sessions = json.load(f)
        
        original_count = len(sessions)
        sessions = [s for s in sessions if s.get('jurisdiction') != jurisdiction]
        removed_count = original_count - len(sessions)
        
        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        print(f"🗑️  Removed {removed_count} learning sessions for jurisdiction '{jurisdiction}'")

def reset_intelligence_data(intelligence_data_dir: str = "./intelligence_data"):
    """Reset intelligence data directory"""
    intelligence_path = Path(intelligence_data_dir)
    
    if intelligence_path.exists() and any(intelligence_path.iterdir()):
        # Backup first - use parent directory with timestamp
        backup_path = intelligence_path.parent / f"{intelligence_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(intelligence_path, backup_path)
        print(f"📁 Backed up intelligence data to: {backup_path}")
    elif intelligence_path.exists():
        # Directory exists but is empty, just remove it
        shutil.rmtree(intelligence_path)
    
    # Recreate empty directory
    intelligence_path.mkdir(exist_ok=True)
    print("🗑️  Intelligence data directory reset")

def show_current_status(learning_data_dir: str = "./learning_data"):
    """Show current learning data status"""
    print("📊 Current Learning Data Status:")
    print("=" * 40)
    
    # Learning sessions
    sessions_file = Path(learning_data_dir) / "learning_sessions.json"
    if sessions_file.exists():
        with open(sessions_file, 'r') as f:
            sessions = json.load(f)
        
        jurisdictions = {}
        for session in sessions:
            jur = session.get('jurisdiction', 'Unknown')
            if jur not in jurisdictions:
                jurisdictions[jur] = {'total': 0, 'successful': 0}
            jurisdictions[jur]['total'] += 1
            if session.get('success'):
                jurisdictions[jur]['successful'] += 1
        
        print(f"Learning Sessions: {len(sessions)} total")
        for jur, stats in jurisdictions.items():
            success_rate = stats['successful'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {jur}: {stats['total']} sessions ({stats['successful']} successful, {success_rate:.1f}%)")
    else:
        print("Learning Sessions: File not found")
    
    # Jurisdiction profiles
    profiles_file = Path(learning_data_dir) / "jurisdiction_profiles.json"
    if profiles_file.exists():
        with open(profiles_file, 'r') as f:
            profiles = json.load(f)
        
        print(f"\nJurisdiction Profiles: {len(profiles)} jurisdictions")
        for jur, data in profiles.items():
            sources = len(data.get('source_profiles', {}))
            total_patterns = sum(len(source.get('extraction_patterns', {})) 
                               for source in data.get('source_profiles', {}).values())
            print(f"  {jur}: {sources} sources, {total_patterns} learned patterns")
    else:
        print("Jurisdiction Profiles: File not found")

def main():
    parser = argparse.ArgumentParser(description="Reset learning data for testing")
    parser.add_argument('--learning-dir', default='./learning_data', 
                      help='Learning data directory (default: ./learning_data)')
    parser.add_argument('--intelligence-dir', default='./intelligence_data',
                      help='Intelligence data directory (default: ./intelligence_data)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show current learning data status')
    
    # Reset commands
    subparsers.add_parser('reset-sessions', help='Reset all learning sessions')
    subparsers.add_parser('reset-profiles', help='Reset all jurisdiction profiles')
    subparsers.add_parser('reset-intelligence', help='Reset intelligence data directory')
    subparsers.add_parser('reset-all', help='Reset everything (sessions + profiles + intelligence)')
    
    # Jurisdiction-specific reset
    reset_jur_parser = subparsers.add_parser('reset-jurisdiction', help='Reset specific jurisdiction')
    reset_jur_parser.add_argument('jurisdiction', help='Jurisdiction name to reset (e.g., "United Kingdom")')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🔧 Learning Data Reset Tool")
    print(f"Learning data directory: {args.learning_dir}")
    print(f"Intelligence data directory: {args.intelligence_dir}")
    print()
    
    # Ensure directories exist
    Path(args.learning_dir).mkdir(exist_ok=True)
    Path(args.intelligence_dir).mkdir(exist_ok=True)
    
    if args.command == 'status':
        show_current_status(args.learning_dir)
    
    elif args.command == 'reset-sessions':
        reset_learning_sessions(args.learning_dir)
    
    elif args.command == 'reset-profiles':
        reset_jurisdiction_profiles(args.learning_dir)
    
    elif args.command == 'reset-intelligence':
        reset_intelligence_data(args.intelligence_dir)
    
    elif args.command == 'reset-all':
        print("🚨 Resetting ALL learning data...")
        reset_learning_sessions(args.learning_dir)
        reset_jurisdiction_profiles(args.learning_dir)
        reset_intelligence_data(args.intelligence_dir)
        print("✅ All learning data reset complete!")
    
    elif args.command == 'reset-jurisdiction':
        reset_specific_jurisdiction(args.jurisdiction, args.learning_dir)
    
    print("\n✅ Operation completed successfully!")

if __name__ == "__main__":
    main()