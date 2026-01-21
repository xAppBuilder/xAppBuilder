# Alpha Backend for xAppBuilder using FastAPI + Supabase + Groq + E2B.


**Run instructions**
cd backend
pip install -r requirements.txt
cp .env.example .env  # Fill in your keys
uvicorn main:app --reload


**This implements Phase 1 from the plan:**
•Basic auth (signup/login/logout via Supabase)
•Project CRUD (simple, no full auth enforcement yet)
•WebSocket live streaming per project
•/build endpoint that triggers a background task
•Background task starts E2B sandbox, uses Groq to "generate" code, streams everything live
•Demo Flutter example (writes a simple app)

**For the MVP:**
•Connect your Next.js frontend chat to POST /projects/{id}/build and open WebSocket at /ws/build/{id}
The terminal will show real-time output
•Extend the agent logic later (add CrewAI, real file parsing, Godot support, etc.)

**Next steps:**
•Add real auth dependency (verify Supabase JWT)
•Store build artifacts in Supabase Storage
•Add proper multi-agent with CrewAI
•Integrate GitHub Actions trigger for Android builds
