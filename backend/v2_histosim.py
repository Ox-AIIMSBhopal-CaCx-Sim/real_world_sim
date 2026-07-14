"""CLI entry point for the histopathology simulation."""

from pathlib import Path
import yaml

if __name__ == "__main__":
    from models.histo import run_histo
    params = yaml.safe_load(Path("parameters/histo_parameters.yaml").read_text())
    run_histo(params)
