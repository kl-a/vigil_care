import type { Metadata } from "next";
import type { ReactNode } from "react";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import "./globals.css";

export const metadata: Metadata = { title: "Vigil", description: "Clinical decision support. The clinician decides." };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-AU">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" />
      </head>
      <body>
        <ViewerProvider>{children}</ViewerProvider>
      </body>
    </html>
  );
}
