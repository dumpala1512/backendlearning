import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Film Search — Frontend Portal",
  description: "Next.js frontend embedding the FastAPI HTMX film search UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0, padding: 0, backgroundColor: "#0f172a" }} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
