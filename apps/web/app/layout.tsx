import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLMOps Platform",
  description: "An LLM gateway and operations dashboard with usage tracking, cost monitoring, and reproducible cloud infrastructure."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
