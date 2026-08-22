import { auth } from "../../../../../../../auth";

export const dynamic = "force-dynamic";

export async function POST(request: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user ? String(session.user.platformUserId) : "";
  if (!platformUserId) return Response.json({ detail: "Authentication required" }, { status: 401 });
  const { sessionId } = await params;
  try {
    const upstream = await fetch(`${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/hermes/sessions/${encodeURIComponent(sessionId)}/chat/stream`, { method: "POST", headers: { "Content-Type": "application/json", "X-Skavan-User-Id": platformUserId }, body: await request.text(), cache: "no-store" });
    return new Response(upstream.body, { status: upstream.status, headers: { "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no" } });
  } catch {
    return Response.json({ detail: "Hermes sessions are unavailable" }, { status: 502 });
  }
}
