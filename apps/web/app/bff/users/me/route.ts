import { auth } from "../../../../auth";

export const dynamic = "force-dynamic";

async function proxy(request?: Request) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user
    ? String(session.user.platformUserId)
    : "";
  if (!platformUserId) {
    return Response.json({ detail: "Authentication required" }, { status: 401 });
  }

  try {
    const upstream = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/users/me${request ? "/preferences/theme" : ""}`,
      {
        method: request ? "PATCH" : "GET",
        headers: {
          "Content-Type": "application/json",
          "X-Skavan-User-Id": platformUserId,
        },
        body: request ? await request.text() : undefined,
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

export async function GET() {
  return proxy();
}

export async function PATCH(request: Request) {
  return proxy(request);
}
