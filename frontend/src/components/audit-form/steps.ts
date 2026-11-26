import type { AuditFormErrors, AuditFormValues } from "@/lib/audit-form";

export type FieldName = keyof AuditFormValues;

export type StepId = "code" | "live" | "login" | "review";

export type StepStatus = "done" | "skipped" | "current" | "upcoming";

export interface StepDef {
  id: StepId;
  /** Short name in the stepper. */
  label: string;
  /** The step heading. */
  title: string;
  /** One help line under the heading. */
  help: string;
  optional: boolean;
  /** Fields validated when leaving the step. */
  fields: readonly FieldName[];
}

export const STEPS: readonly StepDef[] = [
  {
    id: "code",
    label: "Code",
    title: "Your code",
    help: "Add the code of your app. We read it, and we never install or run it.",
    optional: false,
    fields: ["projectName", "repoUrl", "zipFile"],
  },
  {
    id: "live",
    label: "Live site",
    title: "Your live site",
    help: "Add the address where your app runs. We only test a site after you prove it is yours.",
    optional: true,
    fields: ["liveUrl", "domainToken"],
  },
  {
    id: "login",
    label: "Test login",
    title: "Test login",
    help: "Give us a test account so we can check the pages behind your login.",
    optional: true,
    fields: ["journeyEmail", "journeyPassword"],
  },
  {
    id: "review",
    label: "Review",
    title: "Review and run",
    help: "Check what the audit will do, then run it.",
    optional: false,
    fields: [],
  },
];

export const REVIEW_INDEX = STEPS.length - 1;

/** Index of the first step that owns one of the given errors, or -1. */
export function firstStepWithError(errors: AuditFormErrors): number {
  return STEPS.findIndex((step) => step.fields.some((field) => errors[field]));
}

/** Props every input step receives from the form. */
export interface StepFieldProps {
  values: AuditFormValues;
  /** Errors to show now (revealed on blur or on Next). */
  errors: AuditFormErrors;
  onChange: <K extends FieldName>(key: K, value: AuditFormValues[K]) => void;
  onBlur: (key: FieldName) => void;
  disabled: boolean;
}
