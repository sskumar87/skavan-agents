import NextAuth from "next-auth";
import Zitadel from "next-auth/providers/zitadel";

const issuer = process.env.ZITADEL_ISSUER_URL ?? "https://zitadel.invalid";
const clientId = process.env.ZITADEL_CLIENT_ID ?? "zitadel-client-not-configured";

type PlatformUser = {
  id: string;
  preferences: Record<string, unknown>;
};

async function synchronizePlatformUser(idToken: string): Promise<PlatformUser> {
  const response = await fetch(
    `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/auth/sync`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${idToken}` },
      cache: "no-store",
    },
  );
  if (!response.ok) throw new Error("Unable to synchronize the platform user");
  return response.json() as Promise<PlatformUser>;
}

export function buildFederatedLogoutUrl() {
  const appOrigin = process.env.APP_ORIGIN ?? process.env.AUTH_URL ?? "http://localhost:8080";
  const logoutUrl = new URL("/oidc/v1/end_session", issuer);
  logoutUrl.searchParams.set("client_id", clientId);
  logoutUrl.searchParams.set("post_logout_redirect_uri", new URL("/login", appOrigin).toString());
  return logoutUrl.toString();
}

export function isAuthConfigured() {
  return Boolean(
    process.env.AUTH_SECRET
      && process.env.ZITADEL_ISSUER_URL
      && process.env.ZITADEL_CLIENT_ID,
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  basePath: "/auth",
  trustHost: true,
  secret: process.env.AUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: Number(process.env.AUTH_SESSION_MAX_AGE ?? 3600),
  },
  pages: {
    signIn: "/login",
  },
  providers: [
    Zitadel({
      issuer,
      clientId,
      client: {
        token_endpoint_auth_method: "none",
      },
      checks: ["pkce", "state"],
      authorization: {
        params: { scope: "openid profile email" },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, profile, account }) {
      if (profile?.sub) token.externalSubject = profile.sub;
      if (account?.id_token) {
        const platformUser = await synchronizePlatformUser(account.id_token);
        token.platformUserId = platformUser.id;
        token.userPreferences = platformUser.preferences;
      }
      return token;
    },
    session({ session, token }) {
      return {
        ...session,
        user: {
          ...session.user,
          id: String(token.externalSubject ?? token.sub ?? ""),
          platformUserId: String(token.platformUserId ?? ""),
          preferences: token.userPreferences ?? {},
        },
      };
    },
  },
});
