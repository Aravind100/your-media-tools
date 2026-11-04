
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Your Media Tools | Free Online Video & Audio Tools",
  description:
    "Your Media Tools offers online video conversion, MP3 extraction and video compression. Simple, fast and easy-to-use media tools.",
  keywords: [
    "video converter",
    "MP4 converter",
    "MP3 converter",
    "video compressor",
    "online media tools",
    "audio converter",
  ],
  applicationName: "Your Media Tools",
  openGraph: {
    title: "Your Media Tools",
    description:
      "Convert audio, transform videos and compress media online.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
