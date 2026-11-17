import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppProvider } from "@/components/AppProvider";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Budget Pilot",
  description: "Where should we spend the next Rs. 1,000,000? Chat-first ad budget optimizer across 5 platforms.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased">
        <AppProvider>
          <div className="flex h-screen flex-col overflow-hidden">
            <NavBar />
            <main className="min-h-0 flex-1 overflow-y-auto bg-[radial-gradient(ellipse_at_top_right,rgba(233,75,168,0.06),transparent_55%)]">{children}</main>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
