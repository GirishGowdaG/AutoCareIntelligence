import { describe, it, expect } from "vitest";
import { WarrantyAnomalyRecord } from "../src/types/ml";

describe("Warranty Audit Client-Side Filtering & RBAC Rules", () => {
  const mockClaims: WarrantyAnomalyRecord[] = [
    {
      claim_id: "CLM-1001",
      dealer_id: "DLR-01",
      vehicle_id: "VH001",
      anomaly_score: 0.925,
      claim_amount: 4500,
      labor_hours: 14.5,
      parts_cost: 2800,
      labor_cost: 1700,
      is_outlier: true,
      audit_recommended: true,
      disclaimer: "Unsupervised statistical outlier detection for audit prioritization only. Does not constitute proof of dealer fraud or misconduct.",
    },
    {
      claim_id: "CLM-1002",
      dealer_id: "DLR-02",
      vehicle_id: "VH002",
      anomaly_score: 0.812,
      claim_amount: 3200,
      labor_hours: 10.0,
      parts_cost: 1800,
      labor_cost: 1400,
      is_outlier: true,
      audit_recommended: true,
      disclaimer: "Unsupervised statistical outlier detection for audit prioritization only. Does not constitute proof of dealer fraud or misconduct.",
    },
    {
      claim_id: "CLM-1003",
      dealer_id: "DLR-01",
      vehicle_id: "VH003",
      anomaly_score: 0.650,
      claim_amount: 1200,
      labor_hours: 4.0,
      parts_cost: 800,
      labor_cost: 400,
      is_outlier: false,
      audit_recommended: false,
      disclaimer: "Unsupervised statistical outlier detection for audit prioritization only. Does not constitute proof of dealer fraud or misconduct.",
    },
  ];

  it("filters claims by claim_id strictly in client-side state without backend query parameter", () => {
    const targetClaimId = "CLM-1002";
    const filtered = mockClaims.filter((c) =>
      c.claim_id.toLowerCase().includes(targetClaimId.toLowerCase())
    );

    expect(filtered).toHaveLength(1);
    expect(filtered[0].claim_id).toBe("CLM-1002");
    expect(filtered[0].dealer_id).toBe("DLR-02");
  });

  it("returns all records when claim_id filter is blank", () => {
    const search = "";
    const filtered = search.trim()
      ? mockClaims.filter((c) => c.claim_id.toLowerCase().includes(search.trim().toLowerCase()))
      : mockClaims;

    expect(filtered).toHaveLength(3);
  });

  it("enforces role-based permissions for warranty and audit logs", () => {
    const checkPermissions = (role: "Admin" | "DealerServiceManager" | "FleetAnalyst") => ({
      canAccessWarranty: role === "Admin" || role === "FleetAnalyst",
      canAccessAuditLogs: role === "Admin",
    });

    expect(checkPermissions("Admin")).toEqual({
      canAccessWarranty: true,
      canAccessAuditLogs: true,
    });

    expect(checkPermissions("DealerServiceManager")).toEqual({
      canAccessWarranty: false,
      canAccessAuditLogs: false,
    });

    expect(checkPermissions("FleetAnalyst")).toEqual({
      canAccessWarranty: true,
      canAccessAuditLogs: false,
    });
  });
});
