import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatCard } from "../src/components/common/StatCard";
import { EmptyState, ErrorBanner } from "../src/components/common/EmptyState";
import { Activity } from "lucide-react";

describe("Common Components", () => {
  it("renders StatCard with title, value, subtitle and badge", () => {
    render(
      <StatCard
        title="Fleet Vehicles"
        value={50}
        subtitle="Monitored VIN assets"
        badge="Active"
        icon={Activity}
        variant="critical"
      />
    );

    expect(screen.getByText("Fleet Vehicles")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("Monitored VIN assets")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders EmptyState with custom title and description", () => {
    render(
      <EmptyState
        title="No matching assets"
        description="Please adjust your active search parameters."
      />
    );

    expect(screen.getByText("No matching assets")).toBeInTheDocument();
    expect(screen.getByText("Please adjust your active search parameters.")).toBeInTheDocument();
  });

  it("renders ErrorBanner and triggers retry callback", () => {
    const handleRetry = vi.fn();
    render(<ErrorBanner message="Network connection lost" onRetry={handleRetry} />);

    expect(screen.getByText("Network connection lost")).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
