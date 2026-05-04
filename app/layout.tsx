import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataGate",
  description: "Mongolian Financial Document Intelligence"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="datagate-shell min-h-screen antialiased">{children}</body>
    </html>
  );
}
