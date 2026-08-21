import "next-auth";
import "@auth/core/jwt";

declare module "next-auth" {
  interface User {
    platformUserId?: string;
    preferences?: Record<string, unknown>;
    roles?: string[];
  }

  interface Session {
    user: {
      id: string;
      platformUserId: string;
      preferences: Record<string, unknown>;
      roles: string[];
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    externalSubject?: string;
    platformUserId?: string;
    platformGivenName?: string;
    userPreferences?: Record<string, unknown>;
    profileRoles?: string[];
  }
}
