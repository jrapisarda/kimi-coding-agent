export default function Home() {
  return (
    <main style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Chopan Outreach Assistant</h1>
      <p>
        This dashboard surfaces the status of the content, social, email, and prospecting microservices.
      </p>
      <ul>
        <li>Monitor campaign pipeline health</li>
        <li>Review human-in-the-loop approvals</li>
        <li>Trigger snapshots and rollbacks</li>
      </ul>
    </main>
  );
}
