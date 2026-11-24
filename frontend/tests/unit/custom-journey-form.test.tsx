import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useState } from "react";

import { CustomJourneyForm } from "@/components/journey-form";
import type { JourneyStepFormValue } from "@/lib/audit-form";

function Harness({
  initial = [],
  error,
}: {
  initial?: JourneyStepFormValue[];
  error?: string;
}) {
  const [steps, setSteps] = useState<JourneyStepFormValue[]>(initial);
  return <CustomJourneyForm steps={steps} onChange={setSteps} error={error} />;
}

describe("CustomJourneyForm", () => {
  it("shows the default journey as read-only info when empty", () => {
    render(<Harness />);

    expect(
      screen.getByText("Default journey: sign up, log in, add to cart, check out."),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Add a custom step" }),
    ).toBeVisible();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("adds a step row and hides the default info", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));

    expect(
      screen.queryByText(/Default journey:/),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Step 1")).toBeVisible();
    expect(screen.getByLabelText("Action")).toHaveValue("goto");
    expect(screen.getByLabelText("URL")).toBeVisible();
    expect(screen.getByPlaceholderText("/reset-password")).toBeVisible();
  });

  it("removes a step and shows the default info again", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));
    await user.click(screen.getByRole("button", { name: "Remove step 1" }));

    expect(
      screen.getByText("Default journey: sign up, log in, add to cart, check out."),
    ).toBeVisible();
    expect(screen.queryByText("Step 1")).not.toBeInTheDocument();
  });

  it("reorders steps with the move buttons", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));
    await user.click(screen.getByRole("button", { name: "Add step" }));

    const nameInputs = screen.getAllByLabelText(/Step name/);
    const firstName = nameInputs[0];
    const secondName = nameInputs[1];
    if (!firstName || !secondName) throw new Error("expected two name inputs");
    await user.type(firstName, "First");
    await user.type(secondName, "Second");

    await user.click(screen.getByRole("button", { name: "Move step 2 up" }));

    const reordered = screen.getAllByLabelText(/Step name/);
    expect(reordered[0]).toHaveValue("Second");
    expect(reordered[1]).toHaveValue("First");
  });

  it("disables move up on the first step and move down on the last", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));

    expect(
      screen.getByRole("button", { name: "Move step 1 up" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Move step 1 down" }),
    ).toBeDisabled();
  });

  it("shows fill fields when the action is fill", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));
    await user.selectOptions(screen.getByLabelText("Action"), "fill");

    expect(screen.getByLabelText("Selector")).toBeVisible();
    expect(screen.getByLabelText("Value")).toBeVisible();
    expect(screen.queryByLabelText("URL")).not.toBeInTheDocument();
  });

  it("shows the expected text field when the action is expect text", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));
    await user.selectOptions(screen.getByLabelText("Action"), "expect_text");

    expect(screen.getByLabelText("Expected text")).toBeVisible();
    expect(screen.queryByLabelText("URL")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Selector")).not.toBeInTheDocument();
  });

  it("shows the validation error when one is passed", () => {
    render(<Harness error="Step 1: a fill step needs a selector." />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Step 1: a fill step needs a selector.",
    );
  });

  it("keeps each step's fields separate", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Add a custom step" }));
    await user.click(screen.getByRole("button", { name: "Add step" }));

    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    const firstRow = rows[0];
    const secondRow = rows[1];
    if (!firstRow || !secondRow) throw new Error("expected two step rows");
    await user.type(within(firstRow).getByLabelText("URL"), "/reset");
    await user.type(within(secondRow).getByLabelText("URL"), "/login");

    expect(within(firstRow).getByLabelText("URL")).toHaveValue("/reset");
    expect(within(secondRow).getByLabelText("URL")).toHaveValue("/login");
  });
});
