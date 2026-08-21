import NextAuth from "next-auth";
import Zitadel from "next-auth/providers/zitadel";

const issuer = process.env.ZITADEL_ISSUER_URL ?? "https://zitadel.invalid";
const clientId = process.env.ZITADEL_CLIENT_ID ?? "zitadel-client-not-configured";

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
    jwt({ token, profile }) {
      if (profile?.sub) token.externalSubject = profile.sub;
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = String(token.externalSubject ?? token.sub ?? "");
      }
      return session;
    },
  },
});
