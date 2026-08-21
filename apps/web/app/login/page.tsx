import { redirect } from "next/navigation";
import { auth, isAuthConfigured, signIn } from "../../auth";
import { AuthShell } from "../components/auth-shell";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const session = await auth();
  if (session?.user?.id) redirect("/");

  const configured = isAuthConfigured();

  async function signInAction() {
    "use server";
    await signIn("zitadel", { redirectTo: "/" });
  }

  async function registerAction() {
    "use server";
    await signIn("zitadel", { redirectTo: "/" }, { prompt: "create" });
  }

  return <AuthShell configured={configured} signInAction={signInAction} registerAction={registerAction} />;
}
