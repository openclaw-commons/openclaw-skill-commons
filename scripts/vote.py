#!/usr/bin/env python3
"""
OpenClaw Skill Commons - 投票系统 2.0
改进：简化流程 + 时间衰减 + 信誉系统
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

class VotingSystem:
    def __init__(self):
        self.votes_dir = Path('votes')
        self.registry_dir = Path('registry')
        self.leaderboard_file = Path('leaderboard.json')
        
    def get_instance_id(self, hostname, workspace_path):
        """生成唯一实例 ID"""
        data = f"{hostname}:{workspace_path}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def vote(self, skill_name, vote_value, instance_id):
        """
        投票
        vote_value: +1 (有用) 或 -1 (无用)
        """
        # 验证技能是否存在
        skill_file = self.registry_dir / f"{skill_name}.yaml"
        if not skill_file.exists():
            return {'success': False, 'error': 'Skill not found'}
        
        # 检查今日是否已投票
        today = datetime.utcnow().strftime('%Y-%m-%d')
        vote_file = self.votes_dir / instance_id / f"{skill_name}.json"
        
        if vote_file.exists():
            with open(vote_file, 'r') as f:
                last_vote = json.load(f)
            if last_vote.get('date') == today:
                return {'success': False, 'error': 'Already voted today'}
        
        # 记录投票
        vote_file.parent.mkdir(parents=True, exist_ok=True)
        with open(vote_file, 'w') as f:
            json.dump({
                'skill': skill_name,
                'vote': vote_value,
                'date': today,
                'timestamp': datetime.utcnow().isoformat()
            }, f, indent=2)
        
        return {'success': True, 'message': 'Vote recorded'}
    
    def calculate_score(self, votes):
        """
        计算技能分数（带时间衰减）
        """
        if not votes:
            return 0
        
        score = 0
        today = datetime.utcnow()
        
        for vote in votes:
            vote_date = datetime.fromisoformat(vote['timestamp'])
            days_ago = (today - vote_date).days
            
            # 时间衰减：每过一天衰减 5%
            decay = 0.95 ** days_ago
            score += vote['vote'] * decay
        
        return round(score, 2)
    
    def update_leaderboard(self):
        """更新排行榜"""
        # 收集所有投票
        all_votes = {}
        
        for instance_dir in self.votes_dir.glob('*'):
            for vote_file in instance_dir.glob('*.json'):
                with open(vote_file, 'r') as f:
                    vote = json.load(f)
                
                skill = vote['skill']
                if skill not in all_votes:
                    all_votes[skill] = []
                all_votes[skill].append(vote)
        
        # 计算分数
        skills_scores = []
        for skill, votes in all_votes.items():
            score = self.calculate_score(votes)
            positive = sum(1 for v in votes if v['vote'] > 0)
            negative = sum(1 for v in votes if v['vote'] < 0)
            
            skills_scores.append({
                'name': skill,
                'score': score,
                'total_votes': len(votes),
                'positive_votes': positive,
                'negative_votes': negative,
                'unique_voters': len(set(v['timestamp'][:10] for v in votes))
            })
        
        # 排序
        skills_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 更新 leaderboard
        if self.leaderboard_file.exists():
            with open(self.leaderboard_file, 'r') as f:
                leaderboard = json.load(f)
            
            leaderboard['skills'] = skills_scores
            leaderboard['generated_at'] = datetime.utcnow().isoformat() + 'Z'
            
            with open(self.leaderboard_file, 'w') as f:
                json.dump(leaderboard, f, indent=2)
            
            return {'success': True, 'updated': len(skills_scores)}
        
        return {'success': False, 'error': 'Leaderboard not found'}

# CLI 命令
if __name__ == '__main__':
    import sys
    
    voting = VotingSystem()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 vote.py vote <skill> <+1|-1>  # Vote for a skill")
        print("  python3 vote.py update                 # Update leaderboard")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'vote':
        if len(sys.argv) < 4:
            print("Usage: python3 vote.py vote <skill> <+1|-1>")
            sys.exit(1)
        
        skill = sys.argv[2]
        vote_value = int(sys.argv[3])
        instance_id = os.environ.get('OPENCLAW_INSTANCE_ID', 'demo')
        
        result = voting.vote(skill, vote_value, instance_id)
        print(json.dumps(result, indent=2))
    
    elif command == 'update':
        result = voting.update_leaderboard()
        print(json.dumps(result, indent=2))
