import { auth } from "../../../../auth";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return Response.json({ detail: "Authentication required" }, { status: 401 });
  }

  try {
    const upstream = await fetch(`${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/hermes/health`, {
      headers: { "X-Skavan-User-Sub": session.user.id },
      cache: "no-store",
      signal: request.signal,
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ status: "offline" }, { status: 502 });
  }
}
