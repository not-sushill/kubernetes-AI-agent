import type { Metadata } from "next";
import { ReactNode } from "react";

import "./globals.css";

import { Providers } from "@/app/providers";
import { AppShell } from "@/components/layout/app-shell";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
  title: "AI Kubernetes Troubleshooting",
  description: "Production Kubernetes diagnostics and investigation console",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <Providers>
            <AppShell>{children}</AppShell>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}