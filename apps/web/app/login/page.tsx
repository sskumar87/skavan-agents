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

  async function registerAction(formData: FormData) {
    "use server";
    const email = String(formData.get("email") ?? "").trim().toLowerCase();
    if (!email || email.length > 254 || !email.includes("@")) redirect("/login");

    await signIn(
      "zitadel",
      { redirectTo: "/" },
      { prompt: "create", login_hint: email },
    );
  }

  return <AuthShell configured={configured} signInAction={signInAction} registerAction={registerAction} />;
}
