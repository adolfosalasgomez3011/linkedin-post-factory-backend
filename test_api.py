"""
Test client for Post Factory API
"""
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

BASE_URL = "http://localhost:8000"

def test_health():
    """Test API health"""
    console.print("\n[bold cyan]Testing API Health...[/bold cyan]")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        console.print("[green]✓ API is healthy[/green]")
        console.print(json.dumps(data, indent=2))
    else:
        console.print(f"[red]✗ Health check failed: {response.status_code}[/red]")

def test_generate_post():
    """Test post generation"""
    console.print("\n[bold cyan]Testing Post Generation...[/bold cyan]")
    
    payload = {
        "pillar": "technology",
        "format_type": "insight",
        "topic": "AI in predictive maintenance",
        "provider": "claude"
    }
    
    console.print(f"Request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/posts/generate", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            console.print("\n[green]✓ Post generated successfully![/green]")
            
            # Display post
            panel = Panel(
                f"[bold]Text:[/bold]\n{data['text']}\n\n"
                f"[bold]Hashtags:[/bold] {', '.join(data['hashtags'])}\n\n"
                f"[bold]Voice Score:[/bold] {data['voice_score']}/100\n"
                f"[bold]Length:[/bold] {data['length']} chars",
                title=f"Post #{data['id']} - {data['pillar']}",
                border_style="green"
            )
            console.print(panel)
        else:
            console.print(f"[red]✗ Generation failed: {response.status_code}[/red]")
            console.print(response.json())
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

def test_check_voice():
    """Test voice checker"""
    console.print("\n[bold cyan]Testing Voice Checker...[/bold cyan]")
    
    # Bad example (marketing speak)
    bad_text = """
    I'm so excited to announce that I quit my job to follow my passion! 
    My company was amazing but I'm thrilled to start this new journey. 
    It's a game-changer and I'm humbled by all the support.
    """
    
    payload = {"text": bad_text}
    
    try:
        response = requests.post(f"{BASE_URL}/posts/check-voice", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            console.print("\n[yellow]Voice Check Results:[/yellow]")
            console.print(f"Score: {data['score']}/100")
            console.print(f"Grade: {data['grade']}")
            console.print(f"Recommendation: {data['recommendation']}")
            console.print("\nIssues:")
            for issue in data['issues']:
                console.print(f"  {issue}")
        else:
            console.print(f"[red]✗ Voice check failed: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

def test_dashboard():
    """Test dashboard"""
    console.print("\n[bold cyan]Testing Dashboard...[/bold cyan]")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard")
        
        if response.status_code == 200:
            data = response.json()
            console.print("\n[green]✓ Dashboard loaded[/green]")
            console.print(f"Overall Health: {data['overall_health']}/100 (Grade: {data['health_grade']})")
            console.print(f"Next Recommended Pillar: {data['next_recommended_pillar']}")
            
            # Pillar balance table
            if data['pillar_balance']['total_posts'] > 0:
                table = Table(title="Pillar Balance")
                table.add_column("Pillar", style="cyan")
                table.add_column("Current", style="yellow")
                table.add_column("Target", style="green")
                table.add_column("Status", style="bold")
                
                for pillar, balance in data['pillar_balance']['balance'].items():
                    table.add_row(
                        pillar,
                        f"{balance['current']}%",
                        f"{balance['target']}%",
                        balance['status']
                    )
                
                console.print(table)
        else:
            console.print(f"[red]✗ Dashboard failed: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")

def test_list_posts():
    """Test listing posts"""
    console.print("\n[bold cyan]Testing Post Listing...[/bold cyan]")
    
    try:
        response = requests.get(f"{BASE_URL}/posts?limit=5")
        
        if response.status_code == 200:
            posts = response.json()
            console.print(f"\n[green]✓ Found {len(posts)} posts[/green]")
            
            if posts:
                table = Table(title="Recent Posts")
                table.add_column("ID", style="cyan")
                table.add_column("Pillar", style="yellow")
                table.add_column("Score", style="green")
                table.add_column("Length", style="blue")
                table.add_column("Status", style="magenta")
                
                for post in posts:
                    table.add_row(
                        str(post['id']),
                        post['pillar'],
                        f"{post['voice_score']}/100" if post['voice_score'] else "N/A",
                        f"{post['length']} chars",
                        post['status']
                    )
                
                console.print(table)
        else:
            console.print(f"[red]✗ List failed: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")


if __name__ == "__main__":
    console.print("[bold green]Post Factory API Test Suite[/bold green]")
    console.print("=" * 60)
    
    # Run tests
    test_health()
    test_generate_post()
    test_check_voice()
    test_dashboard()
    test_list_posts()
    
    console.print("\n[bold green]All tests complete![/bold green]")
