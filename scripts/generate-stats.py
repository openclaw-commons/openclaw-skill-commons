#!/usr/bin/env python3
"""
OpenClaw Skill Commons - 每日统计生成器
"""

import json
import os
from datetime import datetime
from pathlib import Path

def generate_stats():
    """生成每日统计数据"""
    
    # 读取 leaderboard
    with open('leaderboard.json', 'r') as f:
        leaderboard = json.load(f)
    
    # 统计技能数据
    skills = leaderboard.get('skills', [])
    total_skills = len(skills)
    total_votes = sum(s.get('total_votes', 0) for s in skills)
    positive_votes = sum(s.get('positive_votes', 0) for s in skills)
    
    # 读取投票记录
    votes_dir = Path('votes')
    total_instances = len(list(votes_dir.glob('*'))) if votes_dir.exists() else 0
    
    # 生成统计
    stats = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'total_skills': total_skills,
        'total_votes': total_votes,
        'positive_votes': positive_votes,
        'negative_votes': total_votes - positive_votes,
        'vote_ratio': round(positive_votes / total_votes * 100, 2) if total_votes > 0 else 0,
        'active_instances': total_instances,
        'top_skills': [
            {'name': s['name'], 'score': s['score']}
            for s in sorted(skills, key=lambda x: x['score'], reverse=True)[:10]
        ],
        'trending': [
            {'name': s['name'], 'score_7d': s.get('score_7d', 0)}
            for s in sorted(skills, key=lambda x: x.get('score_7d', 0), reverse=True)[:5]
        ] if leaderboard.get('trending_7d') else []
    }
    
    # 保存统计
    stats_dir = Path('stats')
    stats_dir.mkdir(exist_ok=True)
    
    # 今日统计
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with open(stats_dir / f'{today}.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    # 更新最新统计
    with open(stats_dir / 'latest.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"✅ Stats generated for {today}")
    print(f"   Skills: {total_skills}")
    print(f"   Votes: {total_votes}")
    print(f"   Instances: {total_instances}")

if __name__ == '__main__':
    generate_stats()
