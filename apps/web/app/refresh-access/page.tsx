import { signIn } from "../../auth";

export const dynamic = "force-dynamic";

export default async function RefreshAccessPage() {
  await signIn("zitadel", { redirectTo: "/" });
  return null;
}
