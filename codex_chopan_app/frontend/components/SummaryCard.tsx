interface SummaryCardProps {
  title: string;
  description: string;
}

export function SummaryCard({ title, description }: SummaryCardProps) {
  return (
    <article
      style={{
        border: '1px solid #ddd',
        padding: '1rem',
        borderRadius: '8px',
        marginBottom: '1rem',
        backgroundColor: '#fff',
      }}
    >
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  );
}
