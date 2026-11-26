import type { ReactNode } from "react";

export function PageHeader({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex max-w-prose flex-col gap-2.5">
      <h1 className="text-3xl leading-tight text-balance sm:text-[2.5rem] sm:leading-[1.1]">
        {title}
      </h1>
      {children ? <p className="text-lg text-muted-foreground">{children}</p> : null}
    </div>
  );
}
