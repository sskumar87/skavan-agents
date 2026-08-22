import { redirect } from "next/navigation";
import { auth } from "../auth";
import { ChatClient } from "./chat-client";
import { LogoutButton } from "./components/logout-button";

export const dynamic = "force-dynamic";

type PlatformUserSummary = {
  display_name?: string | null;
  given_name?: string | null;
};

async function loadPlatformUser(platformUserId: string): Promise<PlatformUserSummary | null> {
  if (!platformUserId) return null;
  try {
    const response = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/users/me`,
      {
        headers: { "X-Skavan-User-Id": platformUserId },
        cache: "no-store",
        signal: AbortSignal.timeout(3_000),
      },
    );
    if (!response.ok) return null;
    return response.json() as Promise<PlatformUserSummary>;
  } catch {
    return null;
  }
}

export default async function Home() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");

  const platformUserId = "platformUserId" in session.user
    ? String(session.user.platformUserId ?? "")
    : "";
  const platformUser = await loadPlatformUser(platformUserId);
  const label = platformUser?.given_name?.trim()
    || platformUser?.display_name?.trim().split(/\s+/)[0]
    || session.user.name?.trim().split(/\s+/)[0]
    || session.user.email?.split("@")[0]
    || "Signed in";
  return <ChatClient userName={label} account={<LogoutButton label={label} />} />;
}
