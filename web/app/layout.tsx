import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Nav } from "@/components/nav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PGC Explorer — Psychiatric Genetics Cross-Disorder Analysis",
  description: "Interactive visualization of genetic overlaps across 12 psychiatric disorders using PGC GWAS summary statistics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-100">
        <Nav />
        <main className="mx-auto w-full max-w-[1400px] px-4 py-10 sm:px-8 lg:px-12">
          {children}
        </main>
        <footer className="mt-auto border-t border-zinc-800/50 py-6">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-8 lg:px-12">
            <p className="text-xs text-zinc-600">
              Data from the <span className="text-zinc-500">Psychiatric Genomics Consortium</span> via HuggingFace.
              Visualizations are exploratory — not for clinical use.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
