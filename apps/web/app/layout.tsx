import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Skavan Agents",
  description: "Multi-user collaboration powered by Hermes",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-theme="nerdy-dark">
      <body>{children}</body>
    </html>
  );
}
