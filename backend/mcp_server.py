import os
import json
import httpx
from mcp.server.fastmcp import FastMCP
from google.genai import Client
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("GitHub Card Tools")

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch profile and contribution data for a GitHub user."""
    headers = {}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    async with httpx.AsyncClient(headers=headers) as client:
        # Get user profile
        user_res = await client.get(f"https://api.github.com/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"User {username} not found"}
        user_data = user_res.json()

        # Get repos
        repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30")
        repos = repos_res.json() if repos_res.status_code == 200 else []

        # Sort by stars and get top 6
        top_repos_raw = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
        top_repos = [{
            "name": r["name"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "description": r["description"]
        } for r in top_repos_raw]

        # Aggregate languages
        languages = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        top_langs = [l[0] for l in sorted_langs[:5]]

        return {
            "name": user_data.get("name") or username,
            "avatar_url": user_data.get("avatar_url"),
            "bio": user_data.get("bio"),
            "location": user_data.get("location"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "top_repos": top_repos,
            "top_languages": top_langs
        }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Analyze GitHub data with Gemini to infer dev personality and theme."""
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object:
    {json.dumps(github_data)}

    Return exactly this JSON structure:
    {{
      "developer_vibe": "1 sentence personality",
      "top_skills": ["skill1", "skill2", "skill3"],
      "fun_fact": "something clever inferred from their repos",
      "card_theme": "one of: hacker, builder, researcher, designer, open-source-hero"
    }}
    """
    
    # 1. Try Vertex AI first (Enterprise-grade, no 20 RPD free tier limit!)
    try:
        project_id = os.getenv("GCP_PROJECT", "psyched-battery-496408-k7")
        client = Client(vertexai=True, project=project_id, location="us-central1")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Vertex AI failed during profile analysis: {e}. Falling back to AI Studio...")
        
    # 2. Fall back to AI Studio with sequential model retries
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-pro-latest"
    ]
    
    last_error = None
    try:
        client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
            except Exception as e:
                last_error = e
                print(f"AI Studio fallback warning: Model '{model_name}' failed: {e}")
                continue
    except Exception as e:
        last_error = e
            
    # If all fail, raise the last exception
    raise last_error

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a self-contained, themed HTML card string."""
    theme_colors = {
        "hacker": {"bg": "#0a0a0a", "text": "#00ff41", "accent": "#008f11"},
        "builder": {"bg": "#f0f4f8", "text": "#1a202c", "accent": "#3182ce"},
        "researcher": {"bg": "#ffffff", "text": "#2d3748", "accent": "#805ad5"},
        "designer": {"bg": "#fff5f7", "text": "#4a5568", "accent": "#d53f8c"},
        "open-source-hero": {"bg": "#f0fff4", "text": "#22543d", "accent": "#38a169"}
    }
    
    theme = analysis.get("card_theme", "builder")
    colors = theme_colors.get(theme, theme_colors["builder"])
    
    skills_html = "".join([f'<span class="badge">{s}</span>' for s in analysis.get("top_skills", [])])
    repos_html = "".join([
        f'<div class="repo"><strong>{r["name"]}</strong> ★{r["stars"]} - {r["language"]}</div>' 
        for r in github_data.get("top_repos", [])[:3]
    ])

    html = f"""
    <div class="dev-card theme-{theme}" style="background: {colors['bg']}; color: {colors['text']}; border: 2px solid {colors['accent']}; padding: 20px; border-radius: 15px; width: 350px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 10px 20px rgba(0,0,0,0.2);">
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <img src="{github_data['avatar_url']}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid {colors['accent']}; margin-right: 15px;">
            <div>
                <h2 style="margin: 0; font-size: 1.2rem;">{github_data['name']}</h2>
                <p style="margin: 0; font-size: 0.8rem; opacity: 0.8;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; margin-bottom: 15px; font-size: 0.9rem;">"{analysis['developer_vibe']}"</p>
        <div style="margin-bottom: 15px;">{skills_html}</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; font-size: 0.8rem;">
            <div>📦 {github_data['public_repos']} Repos</div>
            <div>👥 {github_data['followers']} Followers</div>
        </div>
        <div style="border-top: 1px solid {colors['accent']}; padding-top: 10px;">
            <h3 style="font-size: 0.9rem; margin-top: 0;">Top Repos</h3>
            {repos_html}
        </div>
        <p style="font-size: 0.7rem; margin-top: 15px; text-align: right; opacity: 0.6;">✨ {analysis['fun_fact']}</p>
        <style>
            .badge {{ background: {colors['accent']}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; margin-right: 5px; }}
            .repo {{ font-size: 0.75rem; margin-bottom: 5px; }}
        </style>
    </div>
    """
    return html

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the HTML card to a static file and return the path."""
    file_path = f"static/cards/{username}.html"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
