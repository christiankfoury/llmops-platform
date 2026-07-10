import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Production AI Platform",
  description: "LLMOps gateway and usage dashboard"
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
