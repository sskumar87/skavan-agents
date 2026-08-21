"use client";

import { useEffect, useState } from "react";

export function OnboardingClient({ includeWork }: { includeWork: boolean }) {
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function finish() {
      const response = await fetch("/bff/auth/registration-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_work: includeWork }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        if (active) setError(body.detail ?? "Could not finish profile setup");
        return;
      }
      window.location.assign("/refresh-access");
    }
    void finish();
    return () => { active = false; };
  }, [includeWork]);

  return (
    <main className="authPage onboardingPage">
      <section className="uiPanel onboardingPanel" aria-live="polite">
        <img src="/skav-mark.svg" alt="" aria-hidden="true" />
        <span className="authPanelMeta">PROFILE SETUP</span>
        <h1>{error ? "Setup needs attention" : "Preparing your workspace"}</h1>
        <p>{error || `Adding Personal${includeWork ? " and Work" : ""} to your secure login.`}</p>
        {error ? <a className="uiPrimaryAction" href="/login">Return to sign in</a> : <span className="onboardingPulse" aria-hidden="true" />}
      </section>
    </main>
  );
}
