import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

from agent import github_card_agent

app = FastAPI(title="GitHub Dev Card Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup ADK services and runner
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
runner = Runner(
    app_name="GitHubCardGenerator",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
    auto_create_session=True
)

# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Mount static files to serve cards via /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    username: str

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username
    session_id = f"session_{username}"
    
    models_to_try = [
        "projects/psyched-battery-496408-k7/locations/us-central1/publishers/google/models/gemini-2.5-flash",
        "projects/psyched-battery-496408-k7/locations/us-central1/publishers/google/models/gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-pro-latest"
    ]
    
    last_error = None
    for model_name in models_to_try:
        try:
            # Dynamically switch the model on the agent
            github_card_agent.model = model_name
            
            # Recreate runner with updated agent model
            local_runner = Runner(
                app_name="GitHubCardGenerator",
                agent=github_card_agent,
                session_service=session_service,
                memory_service=memory_service,
                auto_create_session=True
            )
            
            from google.genai import types
            new_message = types.Content(
                parts=[types.Part(text=f"Generate a dev card for {username}")]
            )
            
            agent_response_text = ""
            # Run the agent
            async for event in local_runner.run_async(
                user_id="default_user",
                session_id=session_id,
                new_message=new_message
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            agent_response_text += part.text
            
            # The agent's instructions tell it to save the card.
            card_url = f"/static/cards/{username}.html"
            
            return {
                "status": "success",
                "username": username,
                "card_url": card_url,
                "agent_response": agent_response_text
            }
        except Exception as e:
            last_error = e
            print(f"Fallback warning: ADK Agent running with model '{model_name}' failed: {e}")
            continue
            
    # If all fail, raise the last exception
    raise HTTPException(status_code=500, detail=f"All fallback models failed. Last error: {str(last_error)}")

@app.get("/card/{username}")
async def get_card(username: str):
    file_path = os.path.join(CARDS_DIR, f"{username}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Card not found")
    return FileResponse(file_path)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
