import asyncio
import os
from mcp_server import scrape_github, analyze_profile, generate_card_html

async def main():
    username = "torvalds"
    print(f"--- Step 1: Scraping GitHub for {username} ---")
    try:
        github_data = await scrape_github(username)
        if "error" in github_data:
            print(f"Error in scrape_github: {github_data['error']}")
            return
        print("Scrape successful.")
        
        print("\n--- Step 2: Analyzing Profile with Gemini ---")
        analysis = await analyze_profile(github_data)
        print("Analysis successful.")
        
        print("\n--- Step 3: Generating HTML Card ---")
        html = await generate_card_html(username, github_data, analysis)
        print("HTML generation successful.")
        
        print("\n--- Step 4: Results ---")
        print(f"Card Theme: {analysis.get('card_theme')}")
        print(f"Developer Vibe: {analysis.get('developer_vibe')}")
        
        # Save for manual inspection if needed
        with open(f"{username}_test.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nTest card saved to {username}_test.html")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
