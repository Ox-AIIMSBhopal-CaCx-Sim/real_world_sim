"""CLI entry point for the cytopathology simulation."""

from pathlib import Path
import yaml

if __name__ == "__main__":
    from models.cyto import run_cyto
    params = yaml.safe_load(Path("parameters/cyto_parameters.yaml").read_text())
    run_cyto(params)
