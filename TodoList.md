# xAppBuilder MVP Todo List for Cursor Agent

Hey Cursor Agent! This is the prioritized todo list to build the xAppBuilder MVP. We're aiming for a launchable beta in ~10 weeks (target: early April 2026), focusing on **web previews + native Android builds** to differentiate from web-only competitors.

**Project Goals Recap**:
- Users describe app/game ideas via chat.
- Multi-agent system builds it live (stream terminal output).
- Instant web preview + one-click Android APK download.
- Apps: Flutter-based
- Games: Godot 4.x-based (simple 2D to start)
- All on free tiers: Groq, E2B, Supabase, Vercel, GitHub Actions.

**Repo Setup First**:
1. Create a new monorepo (using Turborepo or Nx if needed, but keep simple).
   - Folders: `/frontend` (Next.js), `/backend` (FastAPI), `/agents` (CrewAI/LangGraph scripts).
   - Add README with project overview + this todo list.
   - Initialize Git and push to GitHub (private repo).

### Phase 1: Core Infrastructure (Weeks 1–2)
2. Set up the **frontend** (Next.js 14+ App Router):
   - Create a PWA with mobile-friendly layout.
   - Main page: Chat interface (use shadcn/ui + Tailwind).
   - Add xterm.js terminal panel (collapsible, real-time streaming via WebSockets).
   - Basic project list / new project flow.
   - Deploy to Vercel (free tier).

3. Set up the **backend** (FastAPI):
   - User auth + project storage with Supabase (auth, PostgreSQL, Realtime).
   - WebSocket endpoint for live terminal streaming.
   - API routes: `/start-build` (takes user prompt), `/iterate` (refinement chat).
   - Integrate Groq API for inference (use their Python client).

4. Basic agent loop:
   - Simple single-agent prompt → send to Groq → execute in E2B sandbox → stream output back via WebSocket.
   - Test with "Hello World" Next.js/Flutter page generation + preview.

### Phase 2: Web Apps + Previews (Weeks 3–4)
5. Implement multi-agent crew (use CrewAI or LangGraph):
   - Agents: Planner → Coder → Tester → Asset Generator.
   - Start with Flutter templates in E2B sandbox.
   - Generate simple Flutter apps from prompt.

6. Web previews:
   - Flutter web build in sandbox → serve via E2B preview URL or iframe.
   - Fallback to simple React/Next.js if Flutter web is slow.
   - Add project zip download (full source code).

7. Basic iteration:
   - Store build history in Supabase.
   - Allow follow-up chat messages to refine (re-run agents with context).

### Phase 3: Games + Android Apps (Weeks 5–6)
8. Add Godot support:
   - Create Godot 4.x templates in E2B.
   - Generate simple 2D games (scenes, scripts in GDScript).
   - HTML5 export for instant web preview (iframe).

9. Android builds for apps:
   - Set up GitHub Actions workflow:
     - Clone generated Flutter repo.
     - Build APK/AAB (use `flutter build apk`).
     - Upload artifact → provide download link (store in Supabase Storage).
   - Show progress in UI (poll status).

### Phase 4: Android Games + Polish (Weeks 7–8)
10. Android builds for games:
    - GitHub Actions workflow for Godot Android export.
    - Generate APK → download link.

11. Asset generation:
    - Integrate Fal.ai or Replicate API.
    - Agent can call for sprites, UI images, simple sounds from text descriptions.

12. User accounts & projects:
    - Full Supabase integration: login, project list, save/load builds.

### Phase 5: Final Polish & Launch Prep (Weeks 9–10)
13. Error handling & UX:
    - Timeouts, sandbox cleanup, friendly error messages.
    - Loading states, progress bars for builds (Android can take 10–20 min).

14. Demo content:
    - Seed 3–5 example projects (todo app, calculator, simple platformer game).
    - Landing page on Vercel with marketing copy from pitch deck.

15. Security & limits:
    - Rate limiting, concurrent build limits (stay under free tier quotas).
    - Basic input sanitization.

16. Testing & docs:
    - Manual test all flows.
    - Write basic README + deployment guide.

**General Guidelines for All Tasks**:
- Prioritize reliability over perfection — use tight templates to reduce agent flakiness.
- Log everything for debugging.
- Keep costs zero: no paid services yet.
- Commit often with clear messages.
- If stuck, ask me (Justin) for clarification.

Let's crush this — start with repo setup and Phase 1! 🚀
