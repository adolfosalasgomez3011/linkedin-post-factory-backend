"""
Content Tracker - Monitors pillar balance and posting frequency
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

class ContentTracker:
    def __init__(self, db_path="data/posts.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        self.target_distribution = {
            "asset_management": 0.25,
            "technology": 0.30,
            "consulting": 0.10,
            "entrepreneurship": 0.25,
            "thought_leadership": 0.10
        }
    
    def get_pillar_balance(self, days: int = 30) -> Dict:
        """
        Get current pillar distribution vs target
        
        Args:
            days: Look back period (default 30 days)
            
        Returns:
            Dict with current vs target percentages
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get posts from last N days
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT pillar, COUNT(*) as count
            FROM posts
            WHERE created_at >= ?
            AND status IN ('published', 'scheduled')
            GROUP BY pillar
        """, (cutoff_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                "total_posts": 0,
                "balance": {},
                "recommendations": ["No posts in the selected period. Start creating content!"]
            }
        
        # Calculate current distribution
        total = sum(count for _, count in results)
        current_dist = {pillar: count/total for pillar, count in results}
        
        # Compare to target
        balance = {}
        recommendations = []
        
        for pillar, target_pct in self.target_distribution.items():
            current_pct = current_dist.get(pillar, 0)
            diff = current_pct - target_pct
            
            balance[pillar] = {
                "current": round(current_pct * 100, 1),
                "target": round(target_pct * 100, 1),
                "diff": round(diff * 100, 1),
                "status": "✓" if abs(diff) < 0.10 else "⚠️" if abs(diff) < 0.15 else "❌"
            }
            
            # Generate recommendations
            if diff < -0.15:
                recommendations.append(f"📈 Increase {pillar} posts (currently {round(current_pct*100)}%, target {round(target_pct*100)}%)")
            elif diff > 0.15:
                recommendations.append(f"📉 Reduce {pillar} posts (currently {round(current_pct*100)}%, target {round(target_pct*100)}%)")
        
        return {
            "total_posts": total,
            "period_days": days,
            "balance": balance,
            "recommendations": recommendations or ["✓ Content pillars are well balanced"]
        }
    
    def get_posting_cadence(self, days: int = 30) -> Dict:
        """
        Analyze posting frequency and patterns
        
        Args:
            days: Look back period
            
        Returns:
            Cadence metrics and recommendations
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get all post dates
        cursor.execute("""
            SELECT DATE(created_at) as post_date
            FROM posts
            WHERE created_at >= ?
            AND status IN ('published', 'scheduled')
            ORDER BY created_at
        """, (cutoff_date,))
        
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not dates:
            return {
                "posts_per_week": 0,
                "consistency": "No data",
                "recommendations": ["Start posting! Target: 3-4 posts per week"]
            }
        
        # Calculate metrics
        total_posts = len(dates)
        posts_per_week = (total_posts / days) * 7
        
        # Check consistency (gaps between posts)
        date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        gaps = [(date_objs[i+1] - date_objs[i]).days for i in range(len(date_objs)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        
        # Determine consistency rating
        if avg_gap <= 2.5:
            consistency = "Excellent"
        elif avg_gap <= 4:
            consistency = "Good"
        elif avg_gap <= 7:
            consistency = "Moderate"
        else:
            consistency = "Inconsistent"
        
        # Generate recommendations
        recommendations = []
        
        if posts_per_week < 3:
            recommendations.append("📅 Increase posting frequency (target: 3-4 posts/week)")
        elif posts_per_week > 5:
            recommendations.append("⚠️  Posting too frequently - may reduce engagement quality")
        else:
            recommendations.append("✓ Good posting frequency")
        
        if max_gap > 10:
            recommendations.append(f"⚠️  Longest gap: {max_gap} days - maintain more consistency")
        
        if consistency in ["Good", "Excellent"]:
            recommendations.append("✓ Consistent posting cadence")
        
        return {
            "total_posts": total_posts,
            "posts_per_week": round(posts_per_week, 1),
            "avg_gap_days": round(avg_gap, 1),
            "max_gap_days": max_gap,
            "consistency": consistency,
            "recommendations": recommendations
        }
    
    def get_next_pillar_needed(self) -> str:
        """
        Determine which pillar should be posted next based on balance
        
        Returns:
            Pillar name that needs content most
        """
        balance = self.get_pillar_balance(days=14)  # Check last 2 weeks
        
        if balance["total_posts"] == 0:
            # Start with technology (highest target)
            return "technology"
        
        # Find pillar most under target
        max_deficit = -999
        needed_pillar = "technology"
        
        for pillar, data in balance["balance"].items():
            deficit = data["target"] - data["current"]
            if deficit > max_deficit:
                max_deficit = deficit
                needed_pillar = pillar
        
        return needed_pillar
    
    def get_dashboard(self) -> Dict:
        """
        Get complete content health dashboard
        
        Returns:
            Comprehensive metrics and recommendations
        """
        pillar_balance = self.get_pillar_balance(days=30)
        cadence = self.get_posting_cadence(days=30)
        next_pillar = self.get_next_pillar_needed()
        
        # Overall health score
        balance_score = sum(
            100 if data["status"] == "✓" else 50 if data["status"] == "⚠️" else 0
            for data in pillar_balance["balance"].values()
        ) / len(pillar_balance["balance"])
        
        cadence_score = 100 if cadence["consistency"] in ["Excellent", "Good"] else 50 if cadence["consistency"] == "Moderate" else 0
        
        overall_score = (balance_score + cadence_score) / 2
        
        return {
            "overall_health": round(overall_score, 1),
            "health_grade": "A" if overall_score >= 90 else "B" if overall_score >= 75 else "C" if overall_score >= 60 else "D",
            "pillar_balance": pillar_balance,
            "posting_cadence": cadence,
            "next_recommended_pillar": next_pillar,
            "summary": {
                "total_posts_30d": pillar_balance["total_posts"],
                "posts_per_week": cadence["posts_per_week"],
                "consistency": cadence["consistency"],
                "balance_status": "Good" if balance_score >= 75 else "Needs attention"
            }
        }


if __name__ == "__main__":
    # Test tracker
    tracker = ContentTracker()
    
    print("="*60)
    print("CONTENT HEALTH DASHBOARD")
    print("="*60)
    
    dashboard = tracker.get_dashboard()
    
    print(f"\nOverall Health: {dashboard['overall_health']}/100 (Grade: {dashboard['health_grade']})")
    print(f"\nSummary:")
    print(f"  Total posts (30d): {dashboard['summary']['total_posts_30d']}")
    print(f"  Posts per week: {dashboard['summary']['posts_per_week']}")
    print(f"  Consistency: {dashboard['summary']['consistency']}")
    print(f"  Balance: {dashboard['summary']['balance_status']}")
    
    print(f"\n" + "="*60)
    print("PILLAR BALANCE")
    print("="*60)
    
    if dashboard['pillar_balance']['total_posts'] > 0:
        for pillar, data in dashboard['pillar_balance']['balance'].items():
            print(f"{data['status']} {pillar:20} Current: {data['current']:5.1f}%  Target: {data['target']:5.1f}%  Diff: {data['diff']:+5.1f}%")
    
    print(f"\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    all_recommendations = (
        dashboard['pillar_balance']['recommendations'] + 
        dashboard['posting_cadence']['recommendations']
    )
    
    for rec in all_recommendations:
        print(f"  {rec}")
    
    print(f"\n📝 Next post should be: {dashboard['next_recommended_pillar'].upper()}")
