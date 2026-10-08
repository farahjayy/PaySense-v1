import type { Metadata } from "next";
import "./globals.css";

import { MobileNav, Sidebar } from "@/components/layout/Nav";
import { ToastProvider } from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "PaySense — AI financial copilot",
  description:
    "Cash-flow forecasting and BNPL risk checking for Malaysian Gen-Z students.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <ToastProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="min-w-0 flex-1 px-4 pb-20 pt-5 sm:px-6 md:pb-8">
              <div className="mx-auto w-full max-w-[1200px]">{children}</div>
            </main>
          </div>
          <MobileNav />
        </ToastProvider>
      </body>
    </html>
  );
}
