import { C } from "@/lib/ui";

export function PerforatedEdge({ fill }: { fill?: string }) {
  const c = fill || "var(--purch-paper)";
  return (
    <svg
      width="100%"
      height="10"
      viewBox="0 0 400 10"
      preserveAspectRatio="none"
      style={{ display: "block" }}
    >
      {Array.from({ length: 40 }).map((_, i) => (
        <circle key={i} cx={5 + i * 10} cy="5" r="4" fill={c} />
      ))}
    </svg>
  );
}

export function ReceiptHeader({
  title,
  tone,
}: {
  title: string;
  tone?: string;
}) {
  return (
    <div className="purch-receipt-header">
      <span className="title">{title}</span>
      {tone && <span style={{ opacity: 0.85 }}>{tone}</span>}
    </div>
  );
}
