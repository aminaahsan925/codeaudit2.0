import type { ReactNode } from "react";

export function PageHeader({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex max-w-prose flex-col gap-3">
      <h1 className="text-3xl font-bold tracking-[-0.025em] text-balance">{title}</h1>
      {children ? <p className="text-lg text-muted-foreground">{children}</p> : null}
    </div>
  );
}
