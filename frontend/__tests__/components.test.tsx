import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatCard } from "../src/components/common/StatCard";
import { EmptyState, ErrorBanner, SkeletonTable } from "../src/components/common/EmptyState";
import { LiveTelemetryGauges } from "../src/components/charts/LiveTelemetryGauges";
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

  it("renders EmptyState with custom title and description (Empty State)", () => {
    render(
      <EmptyState
        title="No matching assets"
        description="Please adjust your active search parameters."
      />
    );

    expect(screen.getByText("No matching assets")).toBeInTheDocument();
    expect(screen.getByText("Please adjust your active search parameters.")).toBeInTheDocument();
  });

  it("renders ErrorBanner and triggers retry callback (Error State)", () => {
    const handleRetry = vi.fn();
    render(<ErrorBanner message="Network connection lost" onRetry={handleRetry} />);

    expect(screen.getByText("Network connection lost")).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it("renders SkeletonTable with animated rows (Loading State)", () => {
    const { container } = render(<SkeletonTable rows={6} cols={4} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders LiveTelemetryGauges with strictly the 4 approved verified fields", () => {
    const mockTelemetry = {
      vehicle_id: "VH001",
      rpm: 2450,
      temperature: 92.5,
      battery: 13.8,
      vibration: 1.25,
    };

    render(<LiveTelemetryGauges reading={mockTelemetry} />);

    // Verify exactly the 4 required field labels
    expect(screen.getAllByText("RPM").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Temperature (°C)")).toBeInTheDocument();
    expect(screen.getByText("Battery Voltage (V)")).toBeInTheDocument();
    expect(screen.getByText("Vibration")).toBeInTheDocument();

    // Verify values rendered
    expect(screen.getByText("2450")).toBeInTheDocument();
    expect(screen.getByText("92.5")).toBeInTheDocument();
    expect(screen.getByText("13.8")).toBeInTheDocument();
    expect(screen.getByText("1.25")).toBeInTheDocument();

    // Verify absence of forbidden gauge labels
    expect(screen.queryByText(/Coolant/i)).toBeNull();
    expect(screen.queryByText(/Speed/i)).toBeNull();
    expect(screen.queryByText(/Anomaly Score/i)).toBeNull();
  });
});
