import type { Metadata } from "next";
import { Silkscreen, Press_Start_2P } from "next/font/google";
import "./globals.css";

const silkscreen = Silkscreen({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-silkscreen",
});

const pressStart = Press_Start_2P({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-press-start",
});

export const metadata: Metadata = {
  title: "Offer Loop",
  description: "Automated new-grad job search tracker",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${silkscreen.variable} ${pressStart.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
