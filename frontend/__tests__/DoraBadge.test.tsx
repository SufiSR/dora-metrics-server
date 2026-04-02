/**
 * @jest-environment jsdom
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { DoraBadge } from "@/app/components/dashboard/DoraBadge";

describe("DoraBadge", () => {
  it.each([
    ["ELITE",   "bg-primary"],
    ["HIGH",    "bg-secondary-container"],
    ["MEDIUM",  "bg-tertiary-fixed"],
    ["LOW",     "bg-error-container"],
    ["UNKNOWN", "bg-surface-container"],
  ] as const)("renders %s badge with correct class", (level, expectedClass) => {
    const { container } = render(<DoraBadge level={level} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveTextContent(level);
    expect(badge.className).toContain(expectedClass);
  });
});
