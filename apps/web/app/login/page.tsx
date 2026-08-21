import { redirect } from "next/navigation";
import { auth, isAuthConfigured, signIn } from "../../auth";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const session = await auth();
  if (session?.user?.id) redirect("/");

  const configured = isAuthConfigured();

  return (
    <main className="loginShell">
      <section className="loginCard" aria-labelledby="login-title">
        <div className="brand loginBrand">
          <span className="brandMark" aria-hidden="true">S</span>
          <div><p className="eyebrow">SKAV PLATFORM</p><h1 id="login-title">Agent access</h1></div>
        </div>
        <p className="loginCopy">
          Sign in through the platform identity service to open your private Hermes workspace.
        </p>
        {configured ? (
          <form action={async () => {
            "use server";
            await signIn("zitadel", { redirectTo: "/" });
          }}>
            <button className="loginButton" type="submit">Sign in with ZITADEL</button>
          </form>
        ) : (
          <p className="error" role="alert">
            Login is not configured yet. Add the server-side ZITADEL settings and restart the web service.
          </p>
        )}
        <p className="loginHint">Authorization Code + PKCE · Encrypted HttpOnly session</p>
      </section>
    </main>
  );
}
