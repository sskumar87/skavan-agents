import { auth } from "../../../../auth";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user ? String(session.user.platformUserId) : "";
  if (!platformUserId) return Response.json({ detail: "Authentication required" }, { status: 401 });
  const profile = new URL(request.url).searchParams.get("profile") ?? "";
  try {
    const upstream = await fetch(`${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/hermes/sessions?profile=${encodeURIComponent(profile)}`, { headers: { "X-Skavan-User-Id": platformUserId }, cache: "no-store" });
    return new Response(upstream.body, { status: upstream.status, headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ detail: "Hermes sessions are unavailable" }, { status: 502 });
  }
}
