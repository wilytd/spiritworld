import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Aegis Mesh Dashboard',
  description: 'Home lab maintenance and mesh network management',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{
        margin: 0,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#0f172a',
        color: '#e2e8f0'
      }}>
        {children}
      </body>
    </html>
  )
}
