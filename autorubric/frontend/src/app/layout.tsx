import type { Metadata } from "next";
import { MSWProvider } from "@/components/MSWProvider";
import { QueryProvider } from "@/components/QueryProvider";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Navigation } from "@/components/Navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoRubric — Intelligent Grading & Assessment",
  description: "Autonomous rubric compilation, semantic evaluation, and adversarial security grading.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col bg-[#fbfbfd] text-[#1d1d1f]">
        <QueryProvider>
          <MSWProvider>
            <Navigation />
            <ProtectedRoute>
              <main className="flex-1 px-4 sm:px-8 py-6">
                {children}
              </main>
            </ProtectedRoute>
          </MSWProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
