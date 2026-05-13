"""
Voice Checker - Ensures posts match Adolfo's authentic voice
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class VoiceChecker:
    def __init__(self, config_path="config.json"):
        self.config_path = Path(__file__).parent.parent / config_path
        self.config = self._load_config()
        self.voice_rules = self.config["voice_guidelines"]
    
    def _load_config(self) -> Dict:
        """Load voice guidelines from config"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def check_post(self, text: str) -> Tuple[float, List[str]]:
        """
        Check if post matches voice guidelines
        
        Args:
            text: Post text to check
            
        Returns:
            Tuple of (score 0-100, list of issues)
        """
        issues = []
        score = 100.0
        
        # Check forbidden phrases
        forbidden_issues = self._check_forbidden_phrases(text)
        if forbidden_issues:
            issues.extend(forbidden_issues)
            score -= len(forbidden_issues) * 15  # -15 points per forbidden phrase
        
        # Check authenticity markers
        auth_score, auth_issues = self._check_authenticity(text)
        score = (score + auth_score) / 2  # Average with authenticity score
        issues.extend(auth_issues)
        
        # Check length
        length_issue = self._check_length(text)
        if length_issue:
            issues.append(length_issue)
            score -= 5
        
        # Check paragraph structure
        structure_issue = self._check_structure(text)
        if structure_issue:
            issues.append(structure_issue)
            score -= 10
        
        return max(0, min(100, score)), issues
    
    def _check_forbidden_phrases(self, text: str) -> List[str]:
        """Check for forbidden phrases"""
        issues = []
        text_lower = text.lower()
        
        for phrase in self.voice_rules["forbidden_phrases"]:
            if phrase.lower() in text_lower:
                issues.append(f"❌ Contains forbidden phrase: '{phrase}'")
        
        return issues
    
    def _check_authenticity(self, text: str) -> Tuple[float, List[str]]:
        """Check authenticity markers"""
        score = 50.0  # Start at 50
        issues = []
        text_lower = text.lower()
        
        # Positive markers (add points)
        positive_markers = {
            "specific numbers": [r"\d+%", r"\$\d+", r"\d+ years", r"\d+ months"],
            "operator language": ["ran the numbers", "board demanded", "metal prices", "availability", "uptime"],
            "authentic framing": ["portfolio career", "building ventures", "co-founding with partners"],
            "results focus": ["delivered", "achieved", "reduced by", "improved", "increased"],
            "real examples": ["at southern copper", "at ferreyros", "at chinalco", "through hatch"]
        }
        
        for category, markers in positive_markers.items():
            found = any(marker in text_lower for marker in markers)
            if found:
                score += 10
            else:
                if category in ["specific numbers", "results focus"]:
                    issues.append(f"⚠️  Missing {category}")
        
        # Negative markers (subtract points)
        negative_markers = {
            "marketing speak": ["excited to announce", "thrilled to share", "game-changer", "disruptive"],
            "vague claims": ["world-class", "best-in-class", "cutting-edge", "next-generation" ],
            "humble bragging": ["humbled", "honored", "blessed", "grateful for this journey"],
            "lifestyle content": ["work-life balance", "follow your passion", "do what you love"]
        }
        
        for category, markers in negative_markers.items():
            for marker in markers:
                if marker in text_lower:
                    score -= 15
                    issues.append(f"❌ Contains {category}: '{marker}'")
        
        return score, issues
    
    def _check_length(self, text: str) -> Optional[str]:
        """Check if length is in optimal range"""
        length = len(text)
        
        if length < 800:
            return f"⚠️  Too short ({length} chars, recommended 1,200-1,500)"
        elif length > 2000:
            return f"⚠️  Too long ({length} chars, recommended 1,200-1,500)"
        
        return None
    
    def _check_structure(self, text: str) -> Optional[str]:
        """Check paragraph structure"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 3:
            return "⚠️  Too few paragraphs (need 3-5 for readability)"
        elif len(paragraphs) > 7:
            return "⚠️  Too many paragraphs (keep to 3-5)"
        
        # Check if first paragraph is a good hook (short and punchy)
        if paragraphs and len(paragraphs[0]) > 200:
            return "⚠️  Opening hook too long (should be 1-2 sentences)"
        
        return None
    
    def get_detailed_report(self, text: str) -> Dict:
        """Get comprehensive voice analysis report"""
        score, issues = self.check_post(text)
        
        # Analyze components
        has_hook = len(text.split('\n\n')[0]) < 150 if '\n\n' in text else False
        has_data = any(char.isdigit() for char in text)
        has_cta = any(marker in text.lower() for marker in ['?', 'what', 'how', 'thoughts', 'agree'])
        
        # Calculate sub-scores
        forbidden_check = len([i for i in issues if '❌ Contains forbidden' in i]) == 0
        authenticity_count = len([i for i in issues if i.startswith('⚠️  Missing')]) 
        
        return {
            "overall_score": round(score, 1),
            "grade": self._get_grade(score),
            "issues": issues,
            "components": {
                "hook": "✓" if has_hook else "✗",
                "data/evidence": "✓" if has_data else "✗",
                "call_to_action": "✓" if has_cta else "✗",
                "forbidden_phrases": "✓" if forbidden_check else "✗"
            },
            "length": len(text),
            "length_status": "optimal" if 1200 <= len(text) <= 1500 else "suboptimal",
            "recommendation": self._get_recommendation(score, issues)
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A (Excellent - ready to post)"
        elif score >= 80:
            return "B (Good - minor tweaks)"
        elif score >= 70:
            return "C (Needs work)"
        elif score >= 60:
            return "D (Major revisions needed)"
        else:
            return "F (Regenerate from scratch)"
    
    def _get_recommendation(self, score: float, issues: List[str]) -> str:
        """Get action recommendation"""
        if score >= 85:
            return "✓ Post is authentic and on-brand. Ready to publish."
        elif score >= 70:
            return "⚠️  Post needs minor adjustments. Fix highlighted issues and re-check."
        else:
            forbidden_count = len([i for i in issues if 'forbidden' in i.lower()])
            if forbidden_count > 0:
                return "❌ Contains forbidden phrases. Must regenerate or heavily edit."
            else:
                return "❌ Post doesn't sound like Adolfo. Consider regenerating with different prompt."


if __name__ == "__main__":
    # Test voice checker
    checker = VoiceChecker()
    
    # Bad example (marketing speak)
    bad_post = """Excited to announce that I quit my job to build my company! 🚀
    
    I'm thrilled to share this game-changing journey. Building cutting-edge solutions!
    
    Blessed and grateful for this opportunity. #Entrepreneurship #DreamBig"""
    
    print("="*60)
    print("TESTING BAD POST:")
    print("="*60)
    print(bad_post)
    print("\n" + "="*60)
    report = checker.get_detailed_report(bad_post)
    print(f"Score: {report['overall_score']}/100")
    print(f"Grade: {report['grade']}")
    print(f"\nIssues found:")
    for issue in report['issues']:
        print(f"  {issue}")
    print(f"\nRecommendation: {report['recommendation']}")
    
    # Good example (authentic)
    good_post = """Ran the numbers on our $500M equipment portfolio at Ferreyros: 30% of unplanned downtime came from failures we saw coming three weeks earlier.

The data was there. Vibration sensors showed bearing wear. Oil analysis flagged contamination. Operators noted performance drops in daily reports.

But information lived in six different systems that didn't talk to each other. By the time someone connected the dots, the truck was down for 48 hours instead of 4.

We fixed this by building a single dashboard that aggregated all leading indicators. Not fancy AI—just basic data integration. Reduced unplanned failures by 40% in 12 months.

Most mining companies sit on data gold mines but extract zinc-level value because systems don't integrate. The technology exists. The challenge is organizational, not technical.

What's your biggest barrier to using data you already have?

#MiningOperations #AssetManagement #DataIntegration #PredictiveMaintenance #OperationalExcellence"""
    
    print("\n\n" + "="*60)
    print("TESTING GOOD POST:")
    print("="*60)
    print(good_post)
    print("\n" + "="*60)
    report = checker.get_detailed_report(good_post)
    print(f"Score: {report['overall_score']}/100")
    print(f"Grade: {report['grade']}")
    print(f"\nComponents:")
    for component, status in report['components'].items():
        print(f"  {component}: {status}")
    print(f"\nLength: {report['length']} chars ({report['length_status']})")
    if report['issues']:
        print(f"\nIssues found:")
        for issue in report['issues']:
            print(f"  {issue}")
    print(f"\nRecommendation: {report['recommendation']}")
