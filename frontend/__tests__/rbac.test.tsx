import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ForbiddenView } from "../src/components/common/ForbiddenView";
import { StatusBadge } from "../src/components/common/StatusBadge";
import { AuthRoleProvider } from "../src/context/AuthRoleContext";

describe("RBAC and Component Visibility", () => {
  it("renders ForbiddenView with 403 status and required permission", () => {
    render(
      <AuthRoleProvider>
        <ForbiddenView
          requiredRole="Admin"
          resourceName="Decision Automation Logs"
        />
      </AuthRoleProvider>
    );

    expect(screen.getByText(/403 — Access Forbidden/i)).toBeInTheDocument();
    expect(screen.getByText(/Decision Automation Logs/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Admin/i).length).toBeGreaterThanOrEqual(1);
  });

  it("renders StatusBadge with correct style classes for risk tiers", () => {
    const { container: crit } = render(<StatusBadge status="CRITICAL" />);
    expect(crit.textContent).toBe("CRITICAL");
    expect(crit.firstChild).toHaveClass("text-rose-300");

    const { container: low } = render(<StatusBadge status="LOW" />);
    expect(low.textContent).toBe("LOW");
    expect(low.firstChild).toHaveClass("text-emerald-300");

    const { container: deliv } = render(<StatusBadge status="DELIVERED" />);
    expect(deliv.textContent).toBe("DELIVERED");
    expect(deliv.firstChild).toHaveClass("text-emerald-300");

    const { container: mock } = render(<StatusBadge status="MOCK_LOGGED" />);
    expect(mock.textContent).toBe("MOCK_LOGGED");
    expect(mock.firstChild).toHaveClass("text-blue-300");
  });
});
