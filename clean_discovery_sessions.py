#!/usr/bin/env python3
"""
Clean up discovery sessions - remove duplicates and keep only recent unique sessions
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def clean_discovery_sessions():
    sessions_file = Path.home() / '.claude_regulation_scraper' / 'data' / 'discovery_sessions.json'
    
    if not sessions_file.exists():
        print("No discovery sessions file found")
        return
    
    print(f"📊 Loading discovery sessions from {sessions_file}...")
    
    with open(sessions_file, 'r') as f:
        sessions = json.load(f)
    
    original_count = len(sessions)
    original_size = sessions_file.stat().st_size / 1024 / 1024  # MB
    
    print(f"Original: {original_count} sessions ({original_size:.1f} MB)")
    
    # Group by session_id and target_jurisdictions to find duplicates
    unique_sessions = {}
    jurisdiction_sessions = defaultdict(list)
    
    for session in sessions:
        session_id = session.get('session_id', '')
        jurisdictions = tuple(sorted(session.get('target_jurisdictions', [])))
        start_time_str = session.get('start_time', '')
        
        # Create a unique key
        key = f"{jurisdictions}_{start_time_str}"
        
        if key not in unique_sessions:
            unique_sessions[key] = session
            for jurisdiction in jurisdictions:
                jurisdiction_sessions[jurisdiction].append(session)
    
    print(f"After deduplication: {len(unique_sessions)} unique sessions")
    
    # Keep only the most recent 5 sessions per jurisdiction
    final_sessions = []
    cutoff_date = datetime.utcnow() - timedelta(days=7)  # Keep last 7 days
    
    for jurisdiction, jurisdiction_session_list in jurisdiction_sessions.items():
        # Sort by start_time (newest first) 
        try:
            jurisdiction_session_list.sort(
                key=lambda x: datetime.fromisoformat(x.get('start_time', '')), 
                reverse=True
            )
        except:
            # If datetime parsing fails, just take first few
            pass
        
        # Keep recent and successful sessions
        kept_for_jurisdiction = 0
        for session in jurisdiction_session_list:
            if kept_for_jurisdiction >= 3:  # Max 3 per jurisdiction
                break
                
            try:
                session_date = datetime.fromisoformat(session.get('start_time', ''))
                if session_date > cutoff_date:  # Within last 7 days
                    final_sessions.append(session)
                    kept_for_jurisdiction += 1
            except:
                if kept_for_jurisdiction == 0:  # Keep at least one per jurisdiction
                    final_sessions.append(session)
                    kept_for_jurisdiction += 1
    
    # Remove exact duplicates from final list
    seen = set()
    deduplicated_final = []
    for session in final_sessions:
        session_str = json.dumps(session, sort_keys=True)
        if session_str not in seen:
            seen.add(session_str)
            deduplicated_final.append(session)
    
    final_count = len(deduplicated_final)
    print(f"Final: {final_count} sessions (keeping recent sessions per jurisdiction)")
    
    # Backup original file
    backup_file = sessions_file.with_suffix('.json.backup')
    sessions_file.rename(backup_file)
    print(f"💾 Backed up original to {backup_file.name}")
    
    # Save cleaned data
    with open(sessions_file, 'w') as f:
        json.dump(deduplicated_final, f, indent=2)
    
    new_size = sessions_file.stat().st_size / 1024 / 1024  # MB
    space_saved = original_size - new_size
    
    print(f"✅ Cleanup complete!")
    print(f"📊 Sessions: {original_count} → {final_count}")
    print(f"💾 Size: {original_size:.1f} MB → {new_size:.1f} MB")
    print(f"🎉 Space saved: {space_saved:.1f} MB")
    
    # Show summary by jurisdiction
    print(f"\n📋 Sessions by jurisdiction:")
    jurisdiction_count = defaultdict(int)
    for session in deduplicated_final:
        for jurisdiction in session.get('target_jurisdictions', []):
            jurisdiction_count[jurisdiction] += 1
    
    for jurisdiction, count in sorted(jurisdiction_count.items()):
        print(f"  {jurisdiction}: {count} sessions")

if __name__ == "__main__":
    clean_discovery_sessions()