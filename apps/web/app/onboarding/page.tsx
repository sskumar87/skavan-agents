import { redirect } from "next/navigation";
import { auth } from "../../auth";
import { OnboardingClient } from "./onboarding-client";

export const dynamic = "force-dynamic";

export default async function OnboardingPage({
  searchParams,
}: {
  searchParams: Promise<{ work?: string }>;
}) {
  const session = await auth();
  const platformUserId = session?.user && "platformUserId" in session.user
    ? String(session.user.platformUserId)
    : "";
  if (!platformUserId) redirect("/login");
  const params = await searchParams;
  return <OnboardingClient includeWork={params.work === "1"} />;
}
