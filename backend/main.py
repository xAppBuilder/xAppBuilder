# backend/main.py
import os
import asyncio
import uuid
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from groq import Groq
from e2b_code_interpreter import Sandbox  # Updated import (latest E2B SDK)
import logging

# Setup logging for better debugging (visible in Render logs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="xAppBuilder Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Env vars
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY, E2B_API_KEY]):
    logger.error("Missing required environment variables")
    raise RuntimeError("Missing env vars")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(project_id, []).append(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, message: str):
        if project_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(project_id, conn)

manager = ConnectionManager()

# Models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class BuildRequest(BaseModel):
    prompt: str
    project_type: str = "flutter"  # "flutter" or "godot"

# Auth routes (with better error handling)
@app.post("/auth/signup")
async def signup(user: UserCreate):
    try:
        response = supabase.auth.sign_up({"email": user.email, "password": user.password})
        return response
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        return {"access_token": response.session.access_token, "user": response.user}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

# Projects (improved error handling)
@app.post("/projects")
async def create_project(project: ProjectCreate):
    try:
        data = supabase.table("projects").insert({
            "name": project.name,
            "description": project.description or None,
        }).execute()
        if not data.data:
            raise ValueError("No data returned from insert")
        return data.data[0]
    except Exception as e:
        logger.error(f"Create project error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@app.get("/projects")
async def list_projects():
    try:
        data = supabase.table("projects").select("*").execute()
        return data.data
    except Exception as e:
        logger.error(f"List projects error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

# WebSocket
@app.websocket("/ws/build/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive / future iteration messages
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)

# Improved build task with robust error handling
async def run_build_task(project_id: str, prompt: str, project_type: str = "flutter"):
    await manager.broadcast(project_id, "🚀 Starting AI build...\n")
    
    sandbox = None
    try:
        await manager.broadcast(project_id, "Initializing E2B sandbox...\n")
        sandbox = Sandbox(api_key=E2B_API_KEY)
        await manager.broadcast(project_id, "✅ Sandbox ready\n")

        await manager.broadcast(project_id, "Generating code with Groq...\n")
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are an expert {project_type} developer. Generate a complete project."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.7,
        )
        generated = chat_completion.choices[0].message.content
        await manager.broadcast(project_id, f"Generated code:\n{generated[:1000]}...\n")  # Truncate for stream

        # Demo file write (expand with real parsing later)
        if project_type == "flutter":
            await sandbox.files.write("/home/user/app/lib/main.dart", "import 'package:flutter/material.dart';\n\nvoid main() => runApp(MyApp());\n\nclass MyApp extends StatelessWidget {\n  @override\n  Widget build(BuildContext context) {\n    return MaterialApp(home: Scaffold(body: Center(child: Text('AI-Built App!'))));\n  }\n}")
            await manager.broadcast(project_id, "Wrote main.dart\n")

        await manager.broadcast(project_id, "Build complete! Preview/artifacts coming soon.\n")

    except Exception as e:
        error_msg = f"Build failed: {str(e)}"
        logger.error(error_msg)
        await manager.broadcast(project_id, f"❌ {error_msg}\n")
    finally:
        if sandbox:
            try:
                sandbox.close()
                await manager.broadcast(project_id, "Sandbox closed\n")
            except:
                pass
        await manager.broadcast(project_id, "Build process finished.\n")

@app.post("/projects/{project_id}/build")
async def start_build(project_id: str, request: BuildRequest, background_tasks: BackgroundTasks):
    if not uuid.UUID(project_id, version=4):  # Basic validation
        raise HTTPException(status_code=400, detail="Invalid project ID")
    background_tasks.add_task(run_build_task, project_id, request.prompt, request.project_type)
    return {"message": "Build started successfully"}

@app.get("/")
async def root():
    return {"message": "xAppBuilder Backend Running"}        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, message: str):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id][:]:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(project_id, connection)

manager = ConnectionManager()

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class BuildRequest(BaseModel):
    prompt: str
    project_type: str = "flutter"  # "flutter" or "godot" for MVP

# Basic auth routes using Supabase
@app.post("/auth/signup")
async def signup(user: UserCreate):
    try:
        response = supabase.auth.sign_up({"email": user.email, "password": user.password})
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        return {"access_token": response.session.access_token, "user": response.user}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/logout")
async def logout():
    supabase.auth.sign_out()
    return {"message": "Logged out"}

# Project routes 
@app.post("/projects")
async def create_project(project: ProjectCreate):
    try:
        data = supabase.table("projects").insert({
            "name": project.name,
            "description": project.description or None,  # Handle empty
        }).execute()
        if not data.data:
            raise HTTPException(status_code=400, detail="Insert failed: no data returned")
        return data.data[0]
    except Exception as e:
        # Log full error + return detail for debugging
        print(f"Project insert error: {str(e)}")  # Shows in Render logs
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")
        
@app.get("/projects")
async def list_projects():
    data = supabase.table("projects").select("*").execute()
    return data.data

# WebSocket for live terminal streaming
@app.websocket("/ws/build/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(project_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Optional: handle incoming messages (e.g., iteration prompts)
            await manager.broadcast(project_id, f"Client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)

# Background build task
async def run_build_task(project_id: str, prompt: str, project_type: str = "flutter"):
    await manager.broadcast(project_id, "🚀 Starting build...\n")
    
    try:
        # Start E2B sandbox
        with Sandbox(api_key=E2B_API_KEY) as sandbox:
            await manager.broadcast(project_id, "Sandbox started\n")
            
            # Simple agent prompt to Groq
            system_prompt = f"""
            You are an expert {project_type} developer. Generate a complete, working project based on this description:
            {prompt}
            
            Use best practices. Output only the code files with paths.
            For Flutter: create lib/main.dart and other necessary files.
            For Godot: create project.godot, scenes, and scripts.
            """
            
            await manager.broadcast(project_id, "Generating code with Groq...\n")
            
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-70b-8192",  # Fast and capable
                temperature=0.7,
            )
            
            generated_code = chat_completion.choices[0].message.content
            await manager.broadcast(project_id, f"Generated:\n{generated_code}\n")
            
            # In real agent, parse and write files to sandbox
            # For MVP demo: just echo
            await manager.broadcast(project_id, "Writing files to sandbox...\n")
            
            # Example: write a simple main.dart for Flutter
            if project_type == "flutter":
                sandbox.files.write("/home/user/app/lib/main.dart", """
import 'package:flutter/material.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: Text('xAppBuilder MVP')),
        body: Center(child: Text('Hello from AI-built app!')),
      ),
    );
  }
}
                """)
                await manager.broadcast(project_id, "Wrote main.dart\n")
            
            # Run preview/build commands
            await manager.broadcast(project_id, "Running flutter build web...\n")
            process = await sandbox.process.start("flutter build web")
            await process
            await manager.broadcast(project_id, f"Build complete! Preview at sandbox URL\n")
            
            # Store artifact link, etc.
            
    except Exception as e:
        await manager.broadcast(project_id, f"Error: {str(e)}\n")
    
    await manager.broadcast(project_id, "Build finished.\n")

@app.post("/projects/{project_id}/build")
async def start_build(project_id: str, request: BuildRequest, background_tasks: BackgroundTasks):
    # In production: verify project ownership
    background_tasks.add_task(run_build_task, project_id, request.prompt, request.project_type)
    return {"message": "Build started", "project_id": project_id}

@app.get("/")
async def root():
    return {"message": "xAppBuilder Backend Running"}
