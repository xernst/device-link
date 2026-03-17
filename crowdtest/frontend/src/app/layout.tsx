import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CrowdTest — Test Marketing Before You Spend",
  description:
    "Simulate how real audiences react to your ads, emails, and landing pages.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
