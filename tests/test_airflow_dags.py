"""Unit and structural tests for Airflow DAGs in Phase 4.

Tests DagBag discovery, DAG acyclicity, task dependency order, metadata isolation,
and ingestion manifest tracking.
"""

from pathlib import Path
import pytest

from airflow.models.dagbag import DagBag
from airflow.models.dag import DAG
from airflow.state.manifest import IngestionManifest, compute_sha256

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAirflowDagBag:
    """Test suite for DagBag parsing and discovery."""

    def test_dagbag_discovery_and_no_errors(self):
        dagbag = DagBag()
        assert len(dagbag.import_errors) == 0, f"DagBag import errors: {dagbag.import_errors}"
        expected_dags = {
            "autocare_daily_batch",
            "autocare_streaming_compaction",
            "autocare_sla_monitor",
        }
        assert set(dagbag.dags.keys()) == expected_dags

    @pytest.mark.parametrize(
        "dag_id",
        ["autocare_daily_batch", "autocare_streaming_compaction", "autocare_sla_monitor"],
    )
    def test_dag_acyclicity(self, dag_id):
        dagbag = DagBag()
        dag = dagbag.get_dag(dag_id)
        assert dag is not None
        assert dag.has_cycle() is False, f"Cycle detected in DAG {dag_id}"


class TestDailyBatchPipeline:
    """Test suite for autocare_daily_batch DAG."""

    @pytest.fixture
    def daily_batch_dag(self) -> DAG:
        dagbag = DagBag()
        return dagbag.get_dag("autocare_daily_batch")

    def test_task_count_and_retries(self, daily_batch_dag):
        assert len(daily_batch_dag.tasks) == 9
        assert daily_batch_dag.default_args.get("retries") == 2
        assert daily_batch_dag.default_args.get("email") == ["alerts@autocare.internal"]
        assert daily_batch_dag.default_args.get("email_on_failure") is True

    def test_task_lineage_order(self, daily_batch_dag):
        topo_order = [task.task_id for task in daily_batch_dag.topological_sort()]

        # Verify key milestone ordering
        scan_idx = topo_order.index("scan_and_update_manifest")
        bridge_idx = topo_order.index("bridge_staging_diagnostics")
        load_idx = topo_order.index("load_warehouse_star_schema")
        dbt_run_idx = topo_order.index("dbt_run_models")
        dbt_test_idx = topo_order.index("dbt_test_models")

        assert scan_idx < bridge_idx
        assert bridge_idx < load_idx
        assert load_idx < dbt_run_idx
        assert dbt_run_idx < dbt_test_idx


class TestStreamingCompactionPipeline:
    """Test suite for autocare_streaming_compaction DAG."""

    @pytest.fixture
    def streaming_dag(self) -> DAG:
        dagbag = DagBag()
        return dagbag.get_dag("autocare_streaming_compaction")

    def test_streaming_dag_dependencies(self, streaming_dag):
        assert len(streaming_dag.tasks) == 4
        poll_task = streaming_dag.get_task("poll_streaming_bronze_landing")
        verify_task = streaming_dag.get_task("verify_row_conservation_and_quarantine")
        t_compact = streaming_dag.get_task("compact_telemetry_streaming_to_silver")
        d_compact = streaming_dag.get_task("compact_diagnostics_streaming_to_silver")

        assert t_compact in poll_task.downstream_list
        assert d_compact in poll_task.downstream_list
        assert verify_task in t_compact.downstream_list
        assert verify_task in d_compact.downstream_list


class TestSLAMonitorPipeline:
    """Test suite for autocare_sla_monitor DAG."""

    @pytest.fixture
    def sla_dag(self) -> DAG:
        dagbag = DagBag()
        return dagbag.get_dag("autocare_sla_monitor")

    def test_sla_dag_fan_in(self, sla_dag):
        assert len(sla_dag.tasks) == 4
        heartbeat = sla_dag.get_task("emit_sla_heartbeat_or_alert")
        freshness = sla_dag.get_task("check_warehouse_freshness")
        integrity = sla_dag.get_task("check_star_schema_referential_integrity")
        quarantine = sla_dag.get_task("audit_quarantine_volume")

        assert freshness in heartbeat.upstream_list
        assert integrity in heartbeat.upstream_list
        assert quarantine in heartbeat.upstream_list


class TestMetadataAndManifestIsolation:
    """Test suite ensuring Airflow state is isolated and never alters frozen Bronze."""

    def test_manifest_location_and_bronze_protection(self):
        approved_manifest = REPO_ROOT / "airflow" / "state" / "ingestion_manifest.json"
        forbidden_manifest = REPO_ROOT / "data" / "bronze" / "_ingestion_manifest.json"

        assert approved_manifest.exists(), "Manifest must reside in airflow/state/"
        assert not forbidden_manifest.exists(), "Forbidden manifest found in frozen data/bronze/"

    def test_manifest_tracking_and_hashing(self, tmp_path):
        manifest_file = tmp_path / "test_manifest.json"
        manifest = IngestionManifest(manifest_path=manifest_file)

        # Create dummy file to scan
        sample_dir = tmp_path / "raw"
        sample_dir.mkdir()
        file_a = sample_dir / "dataset_a.csv"
        file_a.write_text("col1,col2\n1,2\n")

        # Scan should detect file_a as new
        scanned = manifest.scan_directory(sample_dir)
        assert len(scanned) == 1
        assert scanned[0][1] is True  # is_new_or_modified

        # Record file in manifest
        manifest.record_processed_file(file_a, sample_dir, batch_id="batch_001")
        manifest.save()

        # Second scan without modification should mark as unchanged
        scanned_again = manifest.scan_directory(sample_dir)
        assert scanned_again[0][1] is False

        # Modifying file should trigger changed state
        file_a.write_text("col1,col2\n1,2\n3,4\n")
        scanned_modified = manifest.scan_directory(sample_dir)
        assert scanned_modified[0][1] is True
