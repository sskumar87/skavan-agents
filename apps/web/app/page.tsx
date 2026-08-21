import { redirect } from "next/navigation";
import { auth } from "../auth";
import { ChatClient } from "./chat-client";
import { LogoutButton } from "./components/logout-button";

export const dynamic = "force-dynamic";

export default async function Home() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");

  const label = session.user.name?.trim().split(/\s+/)[0]
    ?? session.user.email?.split("@")[0]
    ?? "Signed in";
  return <ChatClient userName={label} account={<LogoutButton label={label} />} />;
}
