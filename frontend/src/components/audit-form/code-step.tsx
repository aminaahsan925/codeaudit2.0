import { FileArchive, GitBranch } from "lucide-react";
import type { ChangeEvent } from "react";

import { cn } from "@/lib/utils";

import {
  describedBy,
  FieldError,
  FieldHint,
  FieldLabel,
  formatFileSize,
  inputClasses,
  monoInputClasses,
} from "./field";
import type { StepFieldProps } from "./steps";

export type CodeSource = "repo" | "zip";

const SOURCES: { value: CodeSource; label: string; icon: typeof GitBranch }[] = [
  { value: "repo", label: "GitHub URL", icon: GitBranch },
  { value: "zip", label: "Zip file", icon: FileArchive },
];

/** Two options shown as one control; native radios, so arrow keys work. */
function SourceSwitch({
  value,
  onChange,
  disabled,
}: {
  value: CodeSource;
  onChange: (value: CodeSource) => void;
  disabled: boolean;
}) {
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1.5 text-sm font-medium text-foreground">Where is your code?</legend>
      <div className="inline-grid w-full grid-cols-2 gap-1 rounded-[12px] border border-border bg-sunken p-1 sm:w-auto sm:self-start">
        {SOURCES.map((source) => {
          const Icon = source.icon;
          return (
            <label
              key={source.value}
              className={cn(
                "flex h-9 cursor-pointer items-center justify-center gap-2 rounded-[9px] px-4 text-sm font-medium text-muted-foreground transition-colors select-none hover:text-foreground",
                "has-checked:bg-card has-checked:text-foreground has-checked:shadow-xs dark:has-checked:bg-muted",
                "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ring",
                "has-disabled:cursor-not-allowed has-disabled:opacity-60",
              )}
            >
              <input
                type="radio"
                name="code-source"
                value={source.value}
                checked={value === source.value}
                onChange={() => onChange(source.value)}
                disabled={disabled}
                className="sr-only"
              />
              <Icon aria-hidden="true" className="size-4" />
              {source.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function CodeStep({
  values,
  errors,
  onChange,
  onBlur,
  disabled,
  source,
  onSourceChange,
}: StepFieldProps & {
  source: CodeSource;
  onSourceChange: (source: CodeSource) => void;
}) {
  function onZipChange(event: ChangeEvent<HTMLInputElement>) {
    onChange("zipFile", event.target.files?.[0] ?? null);
  }

  // The "add one of these" error sits on repoUrl in the shared validation.
  // In zip mode the repo field is hidden, so show it under the zip input.
  const zipError = errors.zipFile ?? (values.zipFile === null ? errors.repoUrl : undefined);

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor="project-name">Project name</FieldLabel>
        <input
          id="project-name"
          type="text"
          autoComplete="off"
          maxLength={200}
          value={values.projectName}
          onChange={(event) => onChange("projectName", event.target.value)}
          onBlur={() => onBlur("projectName")}
          aria-invalid={Boolean(errors.projectName)}
          aria-describedby={describedBy(
            "project-name-help",
            errors.projectName && "project-name-error",
          )}
          disabled={disabled}
          placeholder="pocket-notes"
          className={inputClasses}
        />
        <FieldHint id="project-name-help">The name at the top of your report.</FieldHint>
        <FieldError id="project-name-error" message={errors.projectName} />
      </div>

      <div className="flex flex-col gap-4">
        <SourceSwitch value={source} onChange={onSourceChange} disabled={disabled} />

        {source === "repo" ? (
          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="repo-url">GitHub repo URL</FieldLabel>
            <input
              id="repo-url"
              type="url"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              value={values.repoUrl}
              onChange={(event) => onChange("repoUrl", event.target.value)}
              onBlur={() => onBlur("repoUrl")}
              aria-invalid={Boolean(errors.repoUrl)}
              aria-describedby={describedBy("repo-url-help", errors.repoUrl && "repo-url-error")}
              disabled={disabled}
              placeholder="https://github.com/owner/repo"
              className={monoInputClasses}
            />
            <FieldHint id="repo-url-help">
              The repository must be public. For a private one, upload a zip.
            </FieldHint>
            <FieldError id="repo-url-error" message={errors.repoUrl} />
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            <FieldLabel htmlFor="zip-file">Zip upload</FieldLabel>
            <input
              id="zip-file"
              type="file"
              accept=".zip,application/zip"
              onChange={onZipChange}
              aria-invalid={Boolean(zipError)}
              aria-describedby={describedBy("zip-file-help", zipError && "zip-file-error")}
              disabled={disabled}
              className="w-full rounded-[10px] border border-dashed border-input bg-card px-3 py-2.5 text-sm text-muted-foreground outline-none file:mr-3 file:rounded-[8px] file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-sev-critical disabled:opacity-60"
            />
            <FieldHint id="zip-file-help">
              {values.zipFile
                ? `Selected: ${values.zipFile.name}, ${formatFileSize(values.zipFile.size)}.`
                : "A .zip of your project folder, up to 10 MB."}
            </FieldHint>
            <FieldError id="zip-file-error" message={zipError} />
          </div>
        )}
      </div>
    </div>
  );
}
