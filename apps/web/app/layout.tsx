import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./themes.css";
import "./ui-patterns.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Skavan Agents",
  description: "Multi-user collaboration powered by Hermes",
  icons: {
    icon: [{ url: "/skav-mark.svg", type: "image/svg+xml" }],
    shortcut: "/skav-mark.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-theme="neon-grid" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `try{const t=localStorage.getItem("skavan-theme");if(["neon-grid","violet-pulse","amber-terminal","daylight-circuit"].includes(t||""))document.documentElement.dataset.theme=t}catch{}` }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
