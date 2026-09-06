import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/lib/ui";

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
      <body className="min-h-full flex flex-col" style={{ background: '#F5F5F7', padding: '12px' }}>
        <ToastProvider>
          <div className="rounded-[20px] md:rounded-[28px] overflow-hidden shadow-lg" style={{ background: 'var(--purch-bg)' }}>
            {children}
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
