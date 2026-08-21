import { auth } from "../../../../auth";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return Response.json({ detail: "Authentication required" }, { status: 401 });
  }

  try {
    const upstream = await fetch(`${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("content-type") ?? "application/json",
        "X-Skavan-User-Sub": session.user.id,
      },
      body: await request.text(),
      cache: "no-store",
      signal: request.signal,
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Cache-Control": "no-cache, no-store",
        "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return Response.json({ detail: "The platform API is unavailable" }, { status: 502 });
  }
}
