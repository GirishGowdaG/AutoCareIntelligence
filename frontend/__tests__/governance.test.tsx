import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ModelGovernanceDrawer } from "../src/components/governance/ModelGovernanceDrawer";
import { ModelGovernanceResponse } from "../src/types/ml";

describe("ModelGovernanceDrawer", () => {
  const mockGovernance: ModelGovernanceResponse = {
    area_1_failure_risk: {
      area_name: "Area 1: Failure Risk",
      model_name: "GradientBoostingClassifier",
      version: "1.0.0",
      status: "ratified_initial",
      status_display: "RATIFIED (INITIAL)",
      governance_status: "proposed_initial",
      governance_display: "PROPOSED INITIAL THRESHOLD",
      threshold_type: "failure_probability",
      threshold_value: 0.7,
      threshold_label: "Proposed Initial Trigger",
      primary_metric_name: "ROC-AUC",
      primary_metric_value: 0.8452,
      primary_metric_display: "0.8452",
      manifest_path: "data/ml/models/failure_risk/v1.0.0/manifest.json",
      manifest_provenance: "Phase 5 Model Artifacts",
      is_frozen: false,
    },
    area_2_sensor_anomaly: {
      area_name: "Area 2: Sensor Anomaly",
      model_name: "IsolationForestAutoencoderEnsemble",
      version: "1.0.0",
      status: "ratified_frozen",
      status_display: "RATIFIED (FROZEN)",
      governance_status: "frozen",
      governance_display: "FROZEN / APPROVED",
      threshold_type: "composite_reconstruction_error",
      threshold_value: 0.838357,
      threshold_label: "Frozen Calibration Threshold (Phase 5 Method B)",
      primary_metric_name: "F1-Score",
      primary_metric_value: 0.9761,
      primary_metric_display: "0.9761",
      manifest_path: "data/ml/models/sensor_anomaly/v1.0.0/manifest.json",
      manifest_provenance: "Phase 5 Method B Calibration",
      is_frozen: true,
    },
    area_3_service_demand: {
      area_name: "Area 3: Service Demand",
      model_name: "LightGBMForecaster",
      version: "1.0.0",
      status: "ratified_initial",
      status_display: "RATIFIED (INITIAL)",
      governance_status: "proposed_initial",
      governance_display: "PROPOSED INITIAL THRESHOLD",
      threshold_type: "surge_percentage",
      threshold_value: 0.25,
      threshold_label: "Proposed Surge Warning Threshold",
      primary_metric_name: "MAPE",
      primary_metric_value: 0.0812,
      primary_metric_display: "8.12%",
      manifest_path: "data/ml/models/service_demand/v1.0.0/manifest.json",
      manifest_provenance: "Phase 5 Model Artifacts",
      is_frozen: false,
    },
    area_4_warranty_anomaly: {
      area_name: "Area 4: Warranty Anomaly",
      model_name: "IsolationForestOutlierDetector",
      version: "1.0.0",
      status: "ratified_initial",
      status_display: "RATIFIED (INITIAL)",
      governance_status: "proposed_initial",
      governance_display: "PROPOSED INITIAL THRESHOLD",
      threshold_type: "outlier_percentile",
      threshold_value: 0.8,
      threshold_label: "Proposed Audit Prioritization Threshold",
      primary_metric_name: "Precision@Top-K",
      primary_metric_value: 0.4281,
      primary_metric_display: "0.4281",
      manifest_path: "data/ml/models/warranty_anomaly/v1.0.0/manifest.json",
      manifest_provenance: "Phase 5 Model Artifacts",
      is_frozen: false,
    },
    timestamp: "2026-09-27T12:00:00Z",
  };

  it("renders all 4 governance items dynamically without hardcoding", () => {
    render(
      <ModelGovernanceDrawer
        isOpen={true}
        onClose={vi.fn()}
        governance={mockGovernance}
        loading={false}
      />
    );

    // Area 2 Frozen threshold
    expect(screen.getByText(/Area 2: Sensor Anomaly/i)).toBeInTheDocument();
    expect(screen.getByText("0.838357")).toBeInTheDocument();
    expect(screen.getByText(/FROZEN \/ APPROVED/i)).toBeInTheDocument();

    // Area 1 Proposed threshold
    expect(screen.getByText(/Area 1: Failure Risk/i)).toBeInTheDocument();
    expect(screen.getByText("0.7")).toBeInTheDocument();

    // Area 3 Proposed surge
    expect(screen.getByText(/Area 3: Service Demand/i)).toBeInTheDocument();
    expect(screen.getByText("0.25")).toBeInTheDocument();

    // Area 4 Proposed audit
    expect(screen.getByText(/Area 4: Warranty Anomaly/i)).toBeInTheDocument();
    expect(screen.getByText("0.8")).toBeInTheDocument();
  });
});
