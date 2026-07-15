import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import ProgressStepper from "../src/lib/components/ProgressStepper.svelte";
import { PHASES } from "../src/lib/components/ProgressStepper.svelte";

describe("ProgressStepper", () => {
  it("renders all four phase labels in full mode", () => {
    const { getByText } = render(ProgressStepper, { props: { compact: false } });
    for (const phase of PHASES) {
      expect(getByText(phase.label)).toBeInTheDocument();
    }
  });

  it("exposes an aria-live progress region", () => {
    const { container } = render(ProgressStepper);
    const region = container.querySelector('[role="status"]');
    expect(region).not.toBeNull();
    expect(region?.getAttribute("aria-live")).toBe("polite");
  });

  it("hides labels in compact mode", () => {
    const { container } = render(ProgressStepper, {
      props: { compact: true },
    });
    expect(container.querySelector(".stepper.compact")).not.toBeNull();
    expect(container.querySelector(".label")).toBeNull();
  });
});
