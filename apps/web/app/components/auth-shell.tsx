"use client";

import { useEffect, useState } from "react";

const themes = [
  { value: "neon-grid", label: "Neon Grid" },
  { value: "violet-pulse", label: "Violet Pulse" },
  { value: "amber-terminal", label: "Amber Terminal" },
  { value: "daylight-circuit", label: "Daylight Circuit" },
] as const;

type AuthShellProps = {
  configured: boolean;
  signInAction: () => Promise<void>;
  registerAction: (formData: FormData) => Promise<void>;
};

export function AuthShell({ configured, signInAction, registerAction }: AuthShellProps) {
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [theme, setTheme] = useState("neon-grid");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme ?? "neon-grid");
  }, []);

  function selectTheme(value: string) {
    document.documentElement.dataset.theme = value;
    window.localStorage.setItem("skavan-theme", value);
    setTheme(value);
  }

  return (
    <main className="authPage">
      <div className="authWindow">
        <header className="authTopbar">
          <a className="uiBrand" href="/" aria-label="Skav Platform home">
            <img src="/skav-mark.svg" alt="" aria-hidden="true" />
            <span>SKAV PLATFORM</span>
          </a>
          <div className="uiThemePicker" aria-label="Theme selection">
            <span>THEME</span>
            {themes.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`themeSwatch ${item.value}`}
                aria-label={item.label}
                aria-pressed={theme === item.value}
                onClick={() => selectTheme(item.value)}
              ><span /></button>
            ))}
          </div>
        </header>

        <div className="authLayout">
          <section className="authHero" aria-labelledby="auth-product-title">
            <div className="authScanline" aria-hidden="true" />
            <h1 id="auth-product-title">Your private command center for intelligent work.</h1>
          </section>

          <section className="uiPanel authPanel" aria-labelledby="auth-title">
            <div className="authPanelMeta"><span>SECURE ACCESS</span><span>v0.1</span></div>
            <h2 id="auth-title">{mode === "signin" ? "Welcome back" : "Create your identity"}</h2>

            <div className="uiTabs" role="tablist" aria-label="Account action">
              <button type="button" role="tab" aria-selected={mode === "signin"} onClick={() => setMode("signin")}>Sign in</button>
              <button type="button" role="tab" aria-selected={mode === "register"} onClick={() => setMode("register")}>Create account</button>
            </div>

            {configured ? (
              mode === "signin" ? (
                <form action={signInAction} className="authActionForm">
                  <button className="uiPrimaryAction" type="submit">Sign in <ArrowIcon /></button>
                </form>
              ) : (
                <form action={registerAction} className="authActionForm authRegistrationForm">
                  <label className="uiField">
                    Email address
                    <input
                      className="uiInput"
                      type="email"
                      name="email"
                      inputMode="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      required
                    />
                  </label>
                  <button className="uiPrimaryAction" type="submit">Create account <ArrowIcon /></button>
                </form>
              )
            ) : (
              <p className="uiError" role="alert">Login is not configured. Add the server-side ZITADEL settings and restart the web service.</p>
            )}
          </section>
        </div>

        <footer className="authFooter">© 2026 SKAV PLATFORM</footer>
      </div>
    </main>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}
