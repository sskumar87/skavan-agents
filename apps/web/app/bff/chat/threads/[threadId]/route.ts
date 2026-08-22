import { auth } from "../../../../../auth";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ threadId: string }> },
) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user
    ? String(session.user.platformUserId)
    : "";
  if (!platformUserId) return Response.json({ detail: "Authentication required" }, { status: 401 });
  const { threadId } = await params;
  try {
    const upstream = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/chat/threads/${encodeURIComponent(threadId)}`,
      { method: "PATCH", headers: { "Content-Type": "application/json", "X-Skavan-User-Id": platformUserId }, body: await request.text(), cache: "no-store" },
    );
    return new Response(upstream.body, { status: upstream.status, headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ detail: "The platform API is unavailable" }, { status: 502 });
  }
}
