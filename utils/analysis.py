"""Post-simulation analysis pipeline: run folders, manifests, tables, and plots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import urljoin
from urllib.request import pathname2url

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

PathLike = Union[str, Path]

DATA_FILE_NAMES = {
    "patient_timestamps": "patient_timestamps.csv",
    "slide_timestamps": "slide_timestamps.csv",
    "parameters": "parameters.csv",
    "resource_busy_intervals": "resource_busy_intervals.csv",
    "resource_productive_intervals": "resource_productive_intervals.csv",
    "resource_metadata": "resource_metadata.csv",
}
MANIFEST_NAME = "run_manifest.yaml"


def build_run_dir_name(run_timestamp: str, lab: str, tags: str = "") -> str:
    """Build a run folder name like ``20260707_102600_cyto`` or ``..._cyto_integrated``."""
    base = f"{run_timestamp}_{lab}"
    return f"{base}_{tags}" if tags else base


def create_run_directory(
    output_root: PathLike,
    run_timestamp: str,
    lab: str,
    tags: str = "",
) -> Path:
    """Create ``{output_root}/{datetime}_{lab}[_{tags}]``."""
    run_dir = Path(output_root) / build_run_dir_name(run_timestamp, lab, tags)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def path_to_uri(path: PathLike) -> str:
    """Convert a local path to a ``file://`` URI."""
    path = Path(path).resolve()
    return urljoin("file:", pathname2url(str(path)))


def _stringify_paths(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, Path):
            out[key] = str(value.resolve())
        elif isinstance(value, Mapping):
            out[key] = _stringify_paths(value)
        else:
            out[key] = value
    return out


def write_run_manifest(
    run_dir: PathLike,
    *,
    lab: str,
    run_timestamp: str,
    tags: str = "",
    data_paths: Mapping[str, PathLike],
    analysis_paths: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Write ``run_manifest.yaml`` listing data CSVs and analysis outputs."""
    run_dir = Path(run_dir)
    manifest = {
        "run_timestamp": run_timestamp,
        "lab": lab,
        "tags": tags,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_dir": str(run_dir.resolve()),
        "data": {
            key: {
                "path": str(Path(path).resolve()),
                "uri": path_to_uri(path),
            }
            for key, path in data_paths.items()
        },
        "analysis": analysis_paths or {},
    }
    manifest_path = run_dir / MANIFEST_NAME
    with manifest_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(_stringify_paths(manifest), handle, sort_keys=False)
    return manifest_path


def load_run_manifest(run_dir: PathLike) -> Dict[str, Any]:
    """Load ``run_manifest.yaml`` from a run folder."""
    manifest_path = Path(run_dir) / MANIFEST_NAME
    with manifest_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_processes(df: pd.DataFrame) -> list[str]:
    """Return process slugs from ``<Process> Queue`` / ``<Process> Start`` column pairs."""
    cols = [c.strip() for c in df.columns]
    processes: list[str] = []
    seen: set[str] = set()

    for col in cols:
        if not col.endswith(" Queue"):
            continue
        process_name = col[: -len(" Queue")]
        if f"{process_name} Start" not in cols:
            continue
        slug = process_name.lower()
        if slug not in seen:
            processes.append(slug)
            seen.add(slug)
    return processes


def load_waiting_times(path: Optional[PathLike] = None, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Load a dataframe and add ``waiting_for_<process>_days`` columns."""
    if df is None:
        if path is None:
            raise ValueError("Provide either path or df")
        df = pd.read_csv(path, skipinitialspace=True)

    df = df.copy()
    df.columns = df.columns.str.strip()

    processes = list_processes(df)
    if not processes:
        raise ValueError("No processes found: expected '<Process> Queue' and '<Process> Start' columns")

    col_map = {c.lower(): c for c in df.columns}

    datetime_cols: list[str] = []
    for process in processes:
        datetime_cols.extend([col_map[f"{process} queue"], col_map[f"{process} start"]])

    for col in datetime_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .replace("N/A", pd.NA)
        )
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for process in processes:
        queue_col = col_map[f"{process} queue"]
        start_col = col_map[f"{process} start"]
        df[f"waiting_for_{process}_days"] = (
            df[start_col] - df[queue_col]
        ).dt.total_seconds() / (24 * 3600)

    return df


def has_tat_columns(df: pd.DataFrame) -> bool:
    """Return True when ``Arrival`` and ``Reporting End`` columns are present."""
    cols = {c.strip().lower() for c in df.columns}
    return "arrival" in cols and "reporting end" in cols


def calc_tat(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``tat`` (days) and ``tat_moving_avg`` (7-observation rolling mean)."""
    if not has_tat_columns(df):
        raise ValueError("Expected 'Arrival' and 'Reporting End' columns for turnaround time")

    df = df.copy()
    df.columns = df.columns.str.strip()
    col_map = {c.lower(): c for c in df.columns}
    arrival_col = col_map["arrival"]
    reporting_end_col = col_map["reporting end"]

    for col in (arrival_col, reporting_end_col):
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .replace("N/A", pd.NA)
        )
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["tat"] = (
        (df[reporting_end_col] - df[arrival_col]).dt.total_seconds() / (24 * 3600)
    )
    df["tat_moving_avg"] = df["tat"].rolling(window=7, min_periods=1).mean()
    return df


def summarise_tat(df: pd.DataFrame, *, group_name: str = "all") -> pd.DataFrame:
    """Summarise turnaround-time distribution for patient-level results."""
    tat_df = calc_tat(df)
    rows: list[dict[str, Any]] = []

    for stat_name, value in tat_df["tat"].describe().items():
        rows.append(
            {
                "group": group_name,
                "process": "turnaround",
                "stat": stat_name,
                "value": value,
            }
        )
    return pd.DataFrame(rows)


def plot_tat(
    df: pd.DataFrame,
    group_name: Optional[str] = None,
    *,
    output_path: Optional[PathLike] = None,
    show: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot turnaround time per entity and optionally save to disk."""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.plot(df.index, df["tat"], linewidth=1, alpha=0.7, color="steelblue")
    title_group = f" ({group_name})" if group_name else ""
    ax.set_title(f"Turnaround Time{title_group}", fontweight="bold")
    ax.set_xlabel("Entity Number")
    ax.set_ylabel("Turnaround Time (days)")
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig, ax


def analyse_tat(
    filepath: Optional[PathLike] = None,
    df: Optional[pd.DataFrame] = None,
    group_name: Optional[str] = None,
    *,
    output_dir: Optional[PathLike] = None,
    label: str = "tat",
    show: bool = False,
) -> tuple[pd.DataFrame, Optional[Path]]:
    """Compute turnaround-time summaries and optionally save a plot."""
    if df is None and filepath is None:
        raise ValueError("Provide either filepath or df")

    source_df = df if df is not None else pd.read_csv(filepath, skipinitialspace=True)
    if not has_tat_columns(source_df):
        raise ValueError("Expected 'Arrival' and 'Reporting End' columns for turnaround time")

    tat_df = calc_tat(source_df)
    plot_path: Optional[Path] = None

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        group_slug = (group_name or "all").replace(" ", "_")
        plot_path = output_dir / f"{label}_{group_slug}.png"
        plot_tat(tat_df, group_name=group_name, output_path=plot_path, show=show)

    return tat_df, plot_path


def summarise_waiting_times(df: pd.DataFrame, *, group_name: str = "all") -> pd.DataFrame:
    """Summarise waiting-time distributions for each detected process."""
    wait_df = load_waiting_times(df=df)
    rows: list[dict[str, Any]] = []

    for process in list_processes(wait_df):
        series = wait_df[f"waiting_for_{process}_days"]
        stats = series.describe()
        for stat_name, value in stats.items():
            rows.append(
                {
                    "group": group_name,
                    "process": process,
                    "stat": stat_name,
                    "value": value,
                }
            )
    return pd.DataFrame(rows)


def plot_waiting_times(
    df: pd.DataFrame,
    process_name: str,
    group_name: Optional[str] = None,
    *,
    output_path: Optional[PathLike] = None,
    show: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot waiting times for one process and optionally save to disk."""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.plot(
        df.index,
        df[f"waiting_for_{process_name}_days"],
        linewidth=1,
        alpha=0.7,
        color="steelblue",
    )
    title_group = f" and {group_name}" if group_name else ""
    ax.set_title(f"Waiting Time for {process_name}{title_group}", fontweight="bold")
    ax.set_xlabel("Entity Number")
    ax.set_ylabel("Waiting Time (days)")
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig, ax


def analyse_wait_times(
    filepath: Optional[PathLike] = None,
    df: Optional[pd.DataFrame] = None,
    group_name: Optional[str] = None,
    *,
    output_dir: Optional[PathLike] = None,
    label: str = "waiting",
    show: bool = False,
) -> tuple[pd.DataFrame, Dict[str, Path]]:
    """Compute waiting-time summaries and optionally save plots."""
    if df is None and filepath is None:
        raise ValueError("Provide either filepath or df")

    source_df = df if df is not None else pd.read_csv(filepath, skipinitialspace=True)
    wait_df = load_waiting_times(df=source_df)
    summary = summarise_waiting_times(wait_df, group_name=group_name or "all")

    plot_paths: Dict[str, Path] = {}
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        group_slug = (group_name or "all").replace(" ", "_")

        for process in list_processes(wait_df):
            plot_path = output_dir / f"{label}_{process}_{group_slug}.png"
            plot_waiting_times(
                wait_df,
                process,
                group_name=group_name,
                output_path=plot_path,
                show=show,
            )
            plot_paths[process] = plot_path

    return wait_df, plot_paths


STAFF_RESOURCE_TYPES = frozenset({"scheduled", "task_scheduled"})


def _infer_equipment_operator_key(
    equipment_key: str,
    busy_minutes: pd.DataFrame,
    total_minutes: pd.DataFrame,
) -> Optional[str]:
    """
    Infer which staff resource operates a piece of equipment.

    Looks for scheduled staff that appear in the same process intervals as the
    equipment in the busy-interval log.
    """
    equipment_processes = busy_minutes.loc[
        busy_minutes["utilisation_key"] == equipment_key,
        "process_name",
    ].dropna().unique()
    if len(equipment_processes) == 0:
        return None

    staff_keys = {
        key
        for key, resource_type in total_minutes.set_index("utilisation_key")["resource_type"].items()
        if resource_type in STAFF_RESOURCE_TYPES
    }
    if not staff_keys:
        return None

    shared_busy = busy_minutes[
        busy_minutes["process_name"].isin(equipment_processes)
        & busy_minutes["utilisation_key"].isin(staff_keys)
    ]
    if shared_busy.empty:
        return None

    operator_busy = (
        shared_busy.groupby("utilisation_key", as_index=False)["duration_min"]
        .sum()
        .sort_values("duration_min", ascending=False)
    )
    return str(operator_busy.iloc[0]["utilisation_key"])


def _apply_equipment_operator_denominators(
    total_minutes: pd.DataFrame,
    busy_minutes: pd.DataFrame,
    equipment_operator_map: Optional[Mapping[str, str]] = None,
) -> pd.DataFrame:
    """Replace equipment denominators with their operator's scheduled minutes."""
    total_minutes = total_minutes.copy()
    staff_minutes = total_minutes.set_index("utilisation_key")["scheduled_available_minutes"]
    denominator_source = total_minutes["utilisation_key"].copy()

    equipment_operator_map = equipment_operator_map or {}
    equipment_mask = total_minutes["resource_type"] == "equipment"

    for idx, row in total_minutes.loc[equipment_mask].iterrows():
        equipment_key = row["utilisation_key"]
        operator_key = equipment_operator_map.get(equipment_key)
        if operator_key is None:
            operator_key = _infer_equipment_operator_key(
                equipment_key,
                busy_minutes,
                total_minutes,
            )
        if operator_key is None or operator_key not in staff_minutes.index:
            continue

        total_minutes.at[idx, "scheduled_available_minutes"] = staff_minutes.loc[operator_key]
        denominator_source.at[idx] = operator_key

    total_minutes["denominator_source_key"] = denominator_source
    return total_minutes


def calc_res_util_pct(
    busy_minutes: pd.DataFrame,
    total_minutes: pd.DataFrame,
    *,
    equipment_operator_map: Optional[Mapping[str, str]] = None,
) -> pd.DataFrame:
    """Calculate resource utilisation percentages.

    Staff use their rostered ``scheduled_available_minutes``. Equipment uses the
    same denominator as the staff member that operates it (inferred from shared
    busy intervals, or overridden via ``equipment_operator_map``).
    """
    busy_minutes = busy_minutes.copy()
    busy_minutes.columns = busy_minutes.columns.str.strip()
    busy_minutes["utilisation_key"] = busy_minutes["utilisation_key"].str.strip()

    df_res_util_num_sum = (
        busy_minutes
        .groupby("utilisation_key", as_index=False)["duration_min"]
        .sum()
        .sort_values("utilisation_key")
        .reset_index(drop=True)
    )

    total_minutes = _apply_equipment_operator_denominators(
        total_minutes,
        busy_minutes,
        equipment_operator_map=equipment_operator_map,
    )

    df_res_util_den = total_minutes.merge(df_res_util_num_sum, on="utilisation_key", how="left")
    df_res_util_den["available_person_minutes"] = (
        df_res_util_den["capacity"] * df_res_util_den["scheduled_available_minutes"]
    )
    df_res_util_den["utilisation_pct"] = (
        df_res_util_den["duration_min"] / df_res_util_den["available_person_minutes"] * 100
    ).round(2)
    return df_res_util_den.sort_values("utilisation_key").reset_index(drop=True)


def plot_res_util_pct(
    df: pd.DataFrame,
    *,
    output_path: Optional[PathLike] = None,
    show: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot resource utilisation percentages."""
    fig, ax = plt.subplots(figsize=(16, 10))
    bars = ax.bar(
        df["utilisation_key"],
        df["utilisation_pct"],
        linewidth=1,
        alpha=0.7,
        color="steelblue",
    )
    ax.set_ylabel("Utilisation (%)", fontsize=14)
    ax.set_xlabel("Resource", fontsize=14)
    ax.set_title("Utilisation % of Resources", fontsize=16)
    ax.grid(True, alpha=0.3)
    plt.bar_label(
        bars,
        labels=[f"{v:.1f}%" for v in df["utilisation_pct"]],
        padding=3,
        fontsize=14,
    )
    plt.xticks(fontsize=12)
    plt.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.6)
    plt.ylim(0, max(100, df["utilisation_pct"].max() + 10))
    plt.tight_layout()

    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig, ax


def run_analysis(run_dir: PathLike, *, lab: str) -> Dict[str, Any]:
    """
    Run the automated analysis pipeline for a completed simulation run folder.

    Expects the six standard CSV files in ``run_dir`` and writes outputs to
    ``run_dir/analysis/``.
    """
    run_dir = Path(run_dir)
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    tables: Dict[str, Path] = {}
    plots: Dict[str, Path] = {}

    patient_path = run_dir / DATA_FILE_NAMES["patient_timestamps"]
    slide_path = run_dir / DATA_FILE_NAMES["slide_timestamps"]
    busy_path = run_dir / DATA_FILE_NAMES["resource_busy_intervals"]
    metadata_path = run_dir / DATA_FILE_NAMES["resource_metadata"]

    patient_summary_parts: list[pd.DataFrame] = []
    tat_summary_parts: list[pd.DataFrame] = []

    if patient_path.exists():
        patient_df = pd.read_csv(patient_path, skipinitialspace=True)
        include_tat = has_tat_columns(patient_df)

        if "Type" in patient_df.columns:
            for group_value, group_df in patient_df.groupby("Type", dropna=False):
                summary = summarise_waiting_times(group_df, group_name=str(group_value))
                patient_summary_parts.append(summary)
                _, group_plots = analyse_wait_times(
                    df=group_df,
                    group_name=str(group_value),
                    output_dir=analysis_dir,
                    label="waiting_patient",
                )
                for process, plot_path in group_plots.items():
                    plots[f"waiting_patient_{process}_{group_value}"] = plot_path

                if include_tat:
                    tat_summary_parts.append(
                        summarise_tat(group_df, group_name=str(group_value))
                    )
                    _, tat_plot_path = analyse_tat(
                        df=group_df,
                        group_name=str(group_value),
                        output_dir=analysis_dir,
                        label="turnaround_patient",
                    )
                    if tat_plot_path is not None:
                        plots[f"turnaround_patient_{group_value}"] = tat_plot_path
        else:
            patient_summary_parts.append(summarise_waiting_times(patient_df))
            _, patient_plots = analyse_wait_times(
                df=patient_df,
                output_dir=analysis_dir,
                label="waiting_patient",
            )
            for process, plot_path in patient_plots.items():
                plots[f"waiting_patient_{process}"] = plot_path

            if include_tat:
                tat_summary_parts.append(summarise_tat(patient_df))
                _, tat_plot_path = analyse_tat(
                    df=patient_df,
                    output_dir=analysis_dir,
                    label="turnaround_patient",
                )
                if tat_plot_path is not None:
                    plots["turnaround_patient"] = tat_plot_path

    if patient_summary_parts:
        patient_summary = pd.concat(patient_summary_parts, ignore_index=True)
        patient_summary_path = analysis_dir / "waiting_time_patient_summary.csv"
        patient_summary.to_csv(patient_summary_path, index=False)
        tables["waiting_time_patient_summary"] = patient_summary_path

    if tat_summary_parts:
        tat_summary = pd.concat(tat_summary_parts, ignore_index=True)
        tat_summary_path = analysis_dir / "turnaround_time_patient_summary.csv"
        tat_summary.to_csv(tat_summary_path, index=False)
        tables["turnaround_time_patient_summary"] = tat_summary_path

    if slide_path.exists():
        slide_df = pd.read_csv(slide_path, skipinitialspace=True)
        slide_summary = summarise_waiting_times(slide_df, group_name="all")
        slide_summary_path = analysis_dir / "waiting_time_slide_summary.csv"
        slide_summary.to_csv(slide_summary_path, index=False)
        tables["waiting_time_slide_summary"] = slide_summary_path

        _, slide_plots = analyse_wait_times(
            df=slide_df,
            output_dir=analysis_dir,
            label="waiting_slide",
        )
        for process, plot_path in slide_plots.items():
            plots[f"waiting_slide_{process}"] = plot_path

    if busy_path.exists() and metadata_path.exists():
        busy_df = pd.read_csv(busy_path, skipinitialspace=True)
        metadata_df = pd.read_csv(metadata_path, skipinitialspace=True)
        util_df = calc_res_util_pct(busy_df, metadata_df)
        util_table_path = analysis_dir / "resource_utilisation.csv"
        util_df.to_csv(util_table_path, index=False)
        tables["resource_utilisation"] = util_table_path

        util_plot_path = analysis_dir / "resource_utilisation.png"
        plot_res_util_pct(util_df, output_path=util_plot_path)
        plots["resource_utilisation"] = util_plot_path

    analysis_paths = {
        "output_dir": str(analysis_dir.resolve()),
        "tables": {key: str(path.resolve()) for key, path in tables.items()},
        "plots": {key: str(path.resolve()) for key, path in plots.items()},
    }
    return analysis_paths


def finalise_sim_run(
    run_dir: PathLike,
    *,
    lab: str,
    run_timestamp: str,
    data_paths: Mapping[str, PathLike],
    tags: str = "",
    run_post_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Write the run manifest and optionally execute the analysis pipeline.

    ``data_paths`` should point to the six standard CSV outputs inside ``run_dir``.
    """
    run_dir = Path(run_dir)
    resolved_data_paths = {key: Path(path) for key, path in data_paths.items()}

    analysis_paths: Dict[str, Any] = {}
    if run_post_analysis:
        analysis_paths = run_analysis(run_dir, lab=lab)

    manifest_path = write_run_manifest(
        run_dir,
        lab=lab,
        run_timestamp=run_timestamp,
        tags=tags,
        data_paths=resolved_data_paths,
        analysis_paths=analysis_paths,
    )

    return {
        "run_dir": run_dir,
        "manifest": manifest_path,
        "data_paths": resolved_data_paths,
        "analysis": analysis_paths,
    }
