import { redirect } from "next/navigation";
import { buildFederatedLogoutUrl, signOut } from "../../auth";

export function LogoutButton({ label }: { label: string }) {
  return (
    <div className="account">
      <span className="accountName" title={label}>{label}</span>
      <form action={async () => {
        "use server";
        await signOut({ redirect: false });
        redirect(buildFederatedLogoutUrl());
      }}>
        <button className="logoutButton" type="submit">Sign out</button>
      </form>
    </div>
  );
}
