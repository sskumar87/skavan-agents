import { auth } from "../../../../auth";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user
    ? String(session.user.platformUserId)
    : "";
  if (!platformUserId) {
    return Response.json({ detail: "Authentication required" }, { status: 401 });
  }

  try {
    const threadId = new URL(request.url).searchParams.get("thread_id");
    const profile = new URL(request.url).searchParams.get("profile") ?? "personal";
    const params = new URLSearchParams({ profile });
    if (threadId) params.set("thread_id", threadId);
    const upstream = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/chat/history?${params}`,
      {
        headers: { "X-Skavan-User-Id": platformUserId },
        cache: "no-store",
      },
    );
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "The platform API is unavailable" }, { status: 502 });
  }
}
