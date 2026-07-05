"""
Resource utilisation tracking and analysis for DES simulations.

During simulation, ``ResourceUtilisationMonitor`` records two interval types:

- **Held** — from when each resource request is granted until release (includes
  blocked time while waiting for co-resources in the same process).
- **Productive** — from when all resources for the process are acquired
  (service start) until release (active processing only).

After a run, integrate busy server-minutes from the saved CSVs and compute
utilisation percentages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from utils.resource_availability import Schedule

# ---------------------------------------------------------------------------
# Global monitor hook (set once per simulation run)
# ---------------------------------------------------------------------------

_active_monitor: Optional["ResourceUtilisationMonitor"] = None


def set_monitor(monitor: Optional["ResourceUtilisationMonitor"]) -> None:
    global _active_monitor
    _active_monitor = monitor


def get_monitor() -> Optional["ResourceUtilisationMonitor"]:
    return _active_monitor


# ---------------------------------------------------------------------------
# Simulation-time monitor
# ---------------------------------------------------------------------------

@dataclass
class RegisteredResource:
    name: str
    capacity: int
    resource_type: str  # "scheduled", "equipment", "task_scheduled"
    schedule: Optional[Schedule] = None
    task_schedules: Optional[Dict[str, Schedule]] = None


_INTERVAL_COLUMNS = [
    "resource_name",
    "utilisation_key",
    "process_name",
    "task",
    "capacity",
    "start_min",
    "end_min",
    "duration_min",
]


@dataclass
class ResourceUtilisationMonitor:
    """
    Records held and productive busy intervals while the simulation runs.
    """

    simulation_start_datetime: datetime
    held_intervals: List[Dict[str, Any]] = field(default_factory=list)
    productive_intervals: List[Dict[str, Any]] = field(default_factory=list)
    _registry: Dict[int, RegisteredResource] = field(default_factory=dict)
    _open_held_requests: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    _open_productive_requests: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    _request_counter: int = 0

    def register(
        self,
        resource: Any,
        *,
        name: str,
        capacity: int,
        resource_type: str = "equipment",
        schedule: Optional[Schedule] = None,
        task_schedules: Optional[Dict[str, Schedule]] = None,
    ) -> None:
        self._registry[id(resource)] = RegisteredResource(
            name=name,
            capacity=capacity,
            resource_type=resource_type,
            schedule=schedule,
            task_schedules=task_schedules,
        )

    def _lookup(self, resource: Any) -> RegisteredResource:
        meta = self._registry.get(id(resource))
        if meta is None:
            fallback_name = getattr(resource, "name", repr(resource))
            capacity = getattr(resource, "capacity", 1)
            return RegisteredResource(
                name=fallback_name,
                capacity=int(capacity),
                resource_type="equipment",
            )
        return meta

    def _next_request_id(self) -> int:
        self._request_counter += 1
        return self._request_counter

    def _open_interval(
        self,
        store: Dict[int, Dict[str, Any]],
        resource: Any,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> int:
        meta = self._lookup(resource)
        req_id = self._next_request_id()
        store[req_id] = {
            "resource_id": id(resource),
            "resource_name": meta.name,
            "capacity": meta.capacity,
            "process_name": process_name,
            "task": task or "",
            "start_min": float(sim_time),
        }
        return req_id

    def _close_interval(
        self,
        store: Dict[int, Dict[str, Any]],
        target: List[Dict[str, Any]],
        resource: Any,
        req_id: int,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> None:
        open_req = store.pop(req_id, None)
        if open_req is None:
            return

        start_min = open_req["start_min"]
        end_min = float(sim_time)
        if end_min <= start_min:
            return

        meta = self._lookup(resource)
        task_value = task or open_req.get("task") or ""
        target.append(
            {
                "resource_name": meta.name,
                "utilisation_key": _utilisation_key(meta.name, task_value),
                "process_name": process_name,
                "task": task_value,
                "capacity": meta.capacity,
                "start_min": start_min,
                "end_min": end_min,
                "duration_min": end_min - start_min,
            }
        )

    def record_held_start(
        self,
        resource: Any,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> int:
        """Log held time from when this resource request is granted."""
        return self._open_interval(
            self._open_held_requests,
            resource,
            process_name,
            sim_time,
            task=task,
        )

    def record_held_end(
        self,
        resource: Any,
        req_id: int,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> None:
        """Close a held interval opened by ``record_held_start``."""
        self._close_interval(
            self._open_held_requests,
            self.held_intervals,
            resource,
            req_id,
            process_name,
            sim_time,
            task=task,
        )

    def record_productive_start(
        self,
        resource: Any,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> int:
        """Log productive time from when all process resources are ready."""
        return self._open_interval(
            self._open_productive_requests,
            resource,
            process_name,
            sim_time,
            task=task,
        )

    def record_productive_end(
        self,
        resource: Any,
        req_id: int,
        process_name: str,
        sim_time: float,
        *,
        task: Optional[str] = None,
    ) -> None:
        """Close a productive interval opened by ``record_productive_start``."""
        self._close_interval(
            self._open_productive_requests,
            self.productive_intervals,
            resource,
            req_id,
            process_name,
            sim_time,
            task=task,
        )

    # Backwards-compatible aliases (held time)
    def record_start(self, resource: Any, process_name: str, sim_time: float, *, task: Optional[str] = None) -> int:
        return self.record_held_start(resource, process_name, sim_time, task=task)

    def record_end(self, resource: Any, req_id: int, process_name: str, sim_time: float, *, task: Optional[str] = None) -> None:
        self.record_held_end(resource, req_id, process_name, sim_time, task=task)

    def to_held_intervals_dataframe(self) -> pd.DataFrame:
        if not self.held_intervals:
            return pd.DataFrame(columns=_INTERVAL_COLUMNS)
        return pd.DataFrame(self.held_intervals)

    def to_productive_intervals_dataframe(self) -> pd.DataFrame:
        if not self.productive_intervals:
            return pd.DataFrame(columns=_INTERVAL_COLUMNS)
        return pd.DataFrame(self.productive_intervals)

    def to_intervals_dataframe(self) -> pd.DataFrame:
        """Alias for held intervals (backwards compatibility)."""
        return self.to_held_intervals_dataframe()

    def to_metadata_dataframe(
        self,
        *,
        analysis_start_min: float,
        analysis_end_min: float,
    ) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        seen_keys: set[str] = set()

        for meta in self._registry.values():
            keys = [_utilisation_key(meta.name, "")]
            if meta.task_schedules:
                keys.extend(_utilisation_key(meta.name, task) for task in meta.task_schedules)

            for key in keys:
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                task = key.split(" (", 1)[1][:-1] if " (" in key else ""
                schedule = meta.schedule
                if task and meta.task_schedules:
                    schedule = meta.task_schedules.get(task)

                calendar_minutes = max(0.0, analysis_end_min - analysis_start_min)
                scheduled_minutes = calendar_minutes
                if schedule is not None:
                    scheduled_minutes = available_minutes_in_window(
                        schedule,
                        self.simulation_start_datetime,
                        analysis_start_min,
                        analysis_end_min,
                    )
                elif meta.resource_type == "scheduled" and meta.schedule is not None:
                    scheduled_minutes = available_minutes_in_window(
                        meta.schedule,
                        self.simulation_start_datetime,
                        analysis_start_min,
                        analysis_end_min,
                    )

                rows.append(
                    {
                        "utilisation_key": key,
                        "resource_name": meta.name,
                        "task": task,
                        "capacity": meta.capacity,
                        "resource_type": meta.resource_type,
                        "calendar_minutes": calendar_minutes,
                        "scheduled_available_minutes": scheduled_minutes,
                        "analysis_start_min": analysis_start_min,
                        "analysis_end_min": analysis_end_min,
                    }
                )

        return pd.DataFrame(rows)

    def save(
        self,
        output_dir: Union[str, Path],
        run_timestamp: str,
        *,
        analysis_start_min: float,
        analysis_end_min: float,
        prefix: str = "",
    ) -> Dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        label = f"{prefix}_" if prefix else ""
        held_path = output_dir / f"{run_timestamp}_{label}resource_busy_intervals.csv"
        productive_path = output_dir / f"{run_timestamp}_{label}resource_productive_intervals.csv"
        metadata_path = output_dir / f"{run_timestamp}_{label}resource_metadata.csv"

        held_df = self.to_held_intervals_dataframe()
        productive_df = self.to_productive_intervals_dataframe()
        metadata_df = self.to_metadata_dataframe(
            analysis_start_min=analysis_start_min,
            analysis_end_min=analysis_end_min,
        )

        held_df.to_csv(held_path, index=False)
        productive_df.to_csv(productive_path, index=False)
        metadata_df.to_csv(metadata_path, index=False)

        return {
            "intervals": held_path,
            "held_intervals": held_path,
            "productive_intervals": productive_path,
            "metadata": metadata_path,
        }


def _utilisation_key(resource_name: str, task: Optional[str]) -> str:
    if task:
        return f"{resource_name} ({task})"
    return resource_name


# ---------------------------------------------------------------------------
# Schedule geometry (denominator)
# ---------------------------------------------------------------------------

def available_minutes_in_window(
    schedule: Schedule,
    simulation_start_datetime: datetime,
    window_start_min: float,
    window_end_min: float,
) -> float:
    """
    Count rostered on-shift minutes within ``[window_start_min, window_end_min)``.
    """
    if window_end_min <= window_start_min:
        return 0.0

    total = 0.0
    cursor = window_start_min
    while cursor < window_end_min:
        dt = simulation_start_datetime + timedelta(minutes=cursor)
        if schedule.is_available_at(dt):
            total += 1.0
        cursor += 1.0
    return total


def weekday_hourly_available_minutes(
    schedule: Optional[Schedule],
    simulation_start_datetime: datetime,
    window_start_min: float,
    window_end_min: float,
) -> pd.Series:
    """
    Average available minutes per clock hour (0–23) on weekdays (Mon–Fri).

    If ``schedule`` is None, every weekday hour is treated as fully available.
    """
    weekday_counts = {hour: 0 for hour in range(24)}
    weekday_available = {hour: 0.0 for hour in range(24)}

    cursor = window_start_min
    while cursor < window_end_min:
        dt = simulation_start_datetime + timedelta(minutes=cursor)
        if dt.weekday() < 5:
            hour = dt.hour
            weekday_counts[hour] += 1
            if schedule is None or schedule.is_available_at(dt):
                weekday_available[hour] += 1.0
        cursor += 1.0

    avg_available = {}
    for hour in range(24):
        count = weekday_counts[hour]
        avg_available[hour] = weekday_available[hour] / count if count else 0.0

    return pd.Series(avg_available, name="available_minutes")


# ---------------------------------------------------------------------------
# Integral / utilisation computation
# ---------------------------------------------------------------------------

def filter_intervals_post_warmup(
    intervals_df: pd.DataFrame,
    warmup_minutes: float,
) -> pd.DataFrame:
    """Keep only the portion of each interval that lies after warm-up."""
    if intervals_df.empty:
        return intervals_df.copy()

    df = intervals_df.copy()
    df["start_min"] = df["start_min"].clip(lower=warmup_minutes)
    df = df[df["end_min"] > df["start_min"]].copy()
    df["duration_min"] = df["end_min"] - df["start_min"]
    return df


def integrate_busy_minutes(intervals_df: pd.DataFrame) -> float:
    """
    Compute ∫ b(t) dt as the sum of all productive busy interval durations.

    Each interval represents one server busy for ``duration_min`` minutes.
    Overlapping intervals on the same pool are summed (correct for pooled capacity).
    """
    if intervals_df.empty:
        return 0.0
    return float(intervals_df["duration_min"].sum())


def _normalise_task(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _intervals_for_key(
    intervals_df: pd.DataFrame,
    resource_name: str,
    task: str,
) -> pd.DataFrame:
    """Select intervals for a metadata row (pooled or task-specific)."""
    task = _normalise_task(task)
    if task:
        tasks = intervals_df["task"].map(_normalise_task)
        return intervals_df[
            (intervals_df["resource_name"] == resource_name)
            & (tasks == task)
        ]
    return intervals_df[intervals_df["resource_name"] == resource_name]


def compute_utilisation_summary(
    intervals_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    *,
    warmup_minutes: float = 0.0,
    denominator: str = "scheduled",
) -> pd.DataFrame:
    """
    Compute whole-run average utilisation per ``utilisation_key``.

    Parameters
    ----------
    denominator : {"scheduled", "calendar"}
        ``scheduled`` uses rostered on-shift minutes (recommended for staff).
        ``calendar`` uses the full post-warm-up simulation horizon.
    """
    if denominator not in {"scheduled", "calendar"}:
        raise ValueError("denominator must be 'scheduled' or 'calendar'")

    filtered = filter_intervals_post_warmup(intervals_df, warmup_minutes)
    rows: List[Dict[str, Any]] = []

    for _, meta in metadata_df.iterrows():
        key = meta["utilisation_key"]
        task = _normalise_task(meta.get("task", ""))
        resource_name = meta["resource_name"]
        key_intervals = _intervals_for_key(filtered, resource_name, task)

        busy_minutes = integrate_busy_minutes(key_intervals)
        capacity = float(meta["capacity"])
        if denominator == "scheduled":
            available = float(meta["scheduled_available_minutes"])
        else:
            available = float(meta["calendar_minutes"])

        capacity_minutes = capacity * available
        utilisation_pct = (busy_minutes / capacity_minutes * 100.0) if capacity_minutes > 0 else 0.0
        avg_busy_servers = (busy_minutes / available) if available > 0 else 0.0

        rows.append(
            {
                "utilisation_key": key,
                "resource_name": meta["resource_name"],
                "task": task,
                "capacity": int(capacity),
                "resource_type": meta.get("resource_type", ""),
                "busy_server_minutes": round(busy_minutes, 2),
                "available_minutes": round(available, 2),
                "capacity_minutes": round(capacity_minutes, 2),
                "avg_busy_servers": round(avg_busy_servers, 4),
                "utilisation_pct": round(utilisation_pct, 2),
                "denominator": denominator,
            }
        )

    return pd.DataFrame(rows).sort_values("utilisation_key").reset_index(drop=True)


def compute_weekday_hourly_profile(
    intervals_df: pd.DataFrame,
    metadata_row: pd.Series,
    *,
    simulation_start_datetime: datetime,
    warmup_minutes: float = 0.0,
    schedule: Optional[Schedule] = None,
) -> pd.DataFrame:
    """
    Typical weekday utilisation by clock hour (0–23).

    For each hour, utilisation = busy server-minutes in that hour
    ÷ (capacity × average available minutes in that hour across weekdays).
    """
    filtered = filter_intervals_post_warmup(intervals_df, warmup_minutes)
    key = metadata_row["utilisation_key"]
    task = _normalise_task(metadata_row.get("task", ""))
    resource_name = metadata_row["resource_name"]

    key_intervals = _intervals_for_key(filtered, resource_name, task)

    analysis_start = float(metadata_row["analysis_start_min"])
    analysis_end = float(metadata_row["analysis_end_min"])
    capacity = float(metadata_row["capacity"])

    avg_available = weekday_hourly_available_minutes(
        schedule,
        simulation_start_datetime,
        analysis_start,
        analysis_end,
    )

    busy_by_hour = {hour: 0.0 for hour in range(24)}
    for _, row in key_intervals.iterrows():
        start = float(row["start_min"])
        end = float(row["end_min"])
        cursor = start
        while cursor < end:
            dt = simulation_start_datetime + timedelta(minutes=cursor)
            if dt.weekday() < 5:
                busy_by_hour[dt.hour] += 1.0
            cursor += 1.0

    profile_rows = []
    for hour in range(24):
        available = float(avg_available.iloc[hour])
        capacity_minutes = capacity * available
        busy = busy_by_hour[hour]
        util_pct = (busy / capacity_minutes * 100.0) if capacity_minutes > 0 else 0.0
        profile_rows.append(
            {
                "utilisation_key": key,
                "hour": hour,
                "busy_server_minutes": round(busy, 2),
                "avg_available_minutes": round(available, 2),
                "capacity_minutes": round(capacity_minutes, 2),
                "utilisation_pct": round(util_pct, 2),
            }
        )

    return pd.DataFrame(profile_rows)


def load_run_artifacts(
    sim_results_dir: Union[str, Path],
    run_timestamp: str,
    *,
    prefix: str = "",
) -> Dict[str, pd.DataFrame]:
    """
    Load held/productive interval and metadata CSVs for a run.

    Examples
    --------
    Cyto: ``prefix=""`` → ``{timestamp}_resource_busy_intervals.csv``.

    Histo: ``prefix="histo"`` → ``{timestamp}_histo_resource_busy_intervals.csv``.
    """
    sim_results_dir = Path(sim_results_dir)
    label = f"{prefix}_" if prefix else ""

    held_path = sim_results_dir / f"{run_timestamp}_{label}resource_busy_intervals.csv"
    productive_path = sim_results_dir / f"{run_timestamp}_{label}resource_productive_intervals.csv"
    metadata_path = sim_results_dir / f"{run_timestamp}_{label}resource_metadata.csv"

    result = {
        "intervals": pd.read_csv(held_path),
        "held_intervals": pd.read_csv(held_path),
        "metadata": pd.read_csv(metadata_path),
    }
    if productive_path.exists():
        result["productive_intervals"] = pd.read_csv(productive_path)
    else:
        result["productive_intervals"] = pd.DataFrame(columns=_INTERVAL_COLUMNS)
    return result


def analyse_run(
    sim_results_dir: Union[str, Path],
    run_timestamp: str,
    *,
    prefix: str = "",
    warmup_minutes: float = 0.0,
    denominator: str = "scheduled",
    simulation_start_datetime: Optional[datetime] = None,
    schedules_by_key: Optional[Dict[str, Optional[Schedule]]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    End-to-end analysis: held + productive summaries and weekday hourly profiles.
    """
    artifacts = load_run_artifacts(sim_results_dir, run_timestamp, prefix=prefix)
    held_df = artifacts["held_intervals"]
    productive_df = artifacts["productive_intervals"]
    metadata_df = artifacts["metadata"]

    summary_held = compute_utilisation_summary(
        held_df,
        metadata_df,
        warmup_minutes=warmup_minutes,
        denominator=denominator,
    )
    summary_held["interval_type"] = "held"

    summary_productive = compute_utilisation_summary(
        productive_df,
        metadata_df,
        warmup_minutes=warmup_minutes,
        denominator=denominator,
    )
    summary_productive["interval_type"] = "productive"

    summary = pd.concat([summary_held, summary_productive], ignore_index=True)

    profiles_held: List[pd.DataFrame] = []
    profiles_productive: List[pd.DataFrame] = []
    if simulation_start_datetime is not None:
        schedules_by_key = schedules_by_key or {}
        for _, meta_row in metadata_df.iterrows():
            key = meta_row["utilisation_key"]
            schedule = schedules_by_key.get(key)
            if schedule is None and not _normalise_task(meta_row.get("task")):
                schedule = schedules_by_key.get(meta_row["resource_name"])
            profiles_held.append(
                compute_weekday_hourly_profile(
                    held_df,
                    meta_row,
                    simulation_start_datetime=simulation_start_datetime,
                    warmup_minutes=warmup_minutes,
                    schedule=schedule,
                )
            )
            profiles_productive.append(
                compute_weekday_hourly_profile(
                    productive_df,
                    meta_row,
                    simulation_start_datetime=simulation_start_datetime,
                    warmup_minutes=warmup_minutes,
                    schedule=schedule,
                )
            )

    hourly_held = pd.concat(profiles_held, ignore_index=True) if profiles_held else pd.DataFrame()
    hourly_productive = (
        pd.concat(profiles_productive, ignore_index=True) if profiles_productive else pd.DataFrame()
    )
    if not hourly_held.empty:
        hourly_held["interval_type"] = "held"
    if not hourly_productive.empty:
        hourly_productive["interval_type"] = "productive"
    hourly = pd.concat([hourly_held, hourly_productive], ignore_index=True)

    return {
        "summary": summary,
        "summary_held": summary_held,
        "summary_productive": summary_productive,
        "hourly_weekday_profile": hourly,
        "intervals": held_df,
        "held_intervals": held_df,
        "productive_intervals": productive_df,
        "metadata": metadata_df,
    }
