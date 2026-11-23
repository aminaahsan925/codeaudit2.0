import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/*
  A small, safe renderer for the Markdown the API produces in fix guidance:
  `##`/`###` headings, paragraphs, `-` lists, fenced code blocks, and
  inline `code` and **bold**. It renders React nodes only, never HTML, so
  untrusted text cannot inject markup. Anything outside that subset renders
  as plain text.
*/

type Block =
  | { type: "heading"; level: 2 | 3; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "code"; text: string };

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const lines = text.split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i] as string;
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      const code: string[] = [];
      i += 1;
      while (i < lines.length && !(lines[i] as string).trim().startsWith("```")) {
        code.push(lines[i] as string);
        i += 1;
      }
      i += 1; // skip the closing fence (or the end of the text)
      blocks.push({ type: "code", text: code.join("\n") });
      continue;
    }

    if (trimmed.startsWith("## ")) {
      blocks.push({ type: "heading", level: 2, text: trimmed.slice(3).trim() });
      i += 1;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      blocks.push({ type: "heading", level: 3, text: trimmed.slice(4).trim() });
      i += 1;
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const items: string[] = [];
      while (
        i < lines.length &&
        ((lines[i] as string).trim().startsWith("- ") ||
          (lines[i] as string).trim().startsWith("* "))
      ) {
        items.push((lines[i] as string).trim().slice(2).trim());
        i += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    if (trimmed === "") {
      i += 1;
      continue;
    }

    const paragraph: string[] = [];
    while (i < lines.length) {
      const current = (lines[i] as string).trim();
      if (
        current === "" ||
        current.startsWith("```") ||
        current.startsWith("## ") ||
        current.startsWith("### ") ||
        current.startsWith("- ") ||
        current.startsWith("* ")
      ) {
        break;
      }
      paragraph.push(current);
      i += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }
  return blocks;
}

const INLINE_RE = /(`[^`]+`)|(\*\*[^*]+\*\*)/g;

/** Renders inline `code` and **bold**; everything else is plain text. */
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  for (const match of text.matchAll(INLINE_RE)) {
    const index = match.index ?? 0;
    if (index > lastIndex) parts.push(text.slice(lastIndex, index));
    const token = match[0];
    if (token.startsWith("`")) {
      parts.push(
        <code
          key={`${keyPrefix}-${key}`}
          className="rounded-sm bg-muted px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      parts.push(<strong key={`${keyPrefix}-${key}`}>{token.slice(2, -2)}</strong>);
    }
    key += 1;
    lastIndex = index + token.length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export function Markdown({ text, className }: { text: string; className?: string }) {
  const blocks = parseBlocks(text);
  if (blocks.length === 0) return null;
  return (
    <div className={cn("flex flex-col gap-2 text-sm leading-relaxed", className)}>
      {blocks.map((block, index) => {
        switch (block.type) {
          case "heading":
            return block.level === 2 ? (
              <h4 key={index} className="pt-1 text-sm font-semibold">
                {renderInline(block.text, `h${index}`)}
              </h4>
            ) : (
              <h5 key={index} className="pt-1 text-sm font-semibold">
                {renderInline(block.text, `h${index}`)}
              </h5>
            );
          case "list":
            return (
              <ul key={index} className="flex list-disc flex-col gap-1 pl-5">
                {block.items.map((item, itemIndex) => (
                  <li key={itemIndex}>{renderInline(item, `li${index}-${itemIndex}`)}</li>
                ))}
              </ul>
            );
          case "code":
            return (
              <pre
                key={index}
                className="overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-xs leading-relaxed"
              >
                <code>{block.text}</code>
              </pre>
            );
          default:
            return <p key={index}>{renderInline(block.text, `p${index}`)}</p>;
        }
      })}
    </div>
  );
}
