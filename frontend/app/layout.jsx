import './globals.css';

export const metadata = {
  title: 'Ledger | Autonomous Agent Intelligence Hub',
  description: 'Real-time multi-agent compliance extraction, guardrails & execution state graph streamer',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
