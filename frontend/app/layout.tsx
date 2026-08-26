import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Purch — Budget tracking, reimagined",
  description:
    "Log expenses the way you text — casually. Purch extracts the item, amount, and category, and reacts in the tone you pick.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[color:var(--purch-parchment)] text-[color:var(--purch-ink)]">
        {children}
      </body>
    </html>
  );
}
