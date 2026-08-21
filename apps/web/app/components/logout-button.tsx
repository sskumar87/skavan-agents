import { signOut } from "../../auth";

export function LogoutButton({ label }: { label: string }) {
  return (
    <div className="account">
      <span className="accountName" title={label}>{label}</span>
      <form action={async () => {
        "use server";
        await signOut({ redirectTo: "/login" });
      }}>
        <button className="logoutButton" type="submit">Sign out</button>
      </form>
    </div>
  );
}
