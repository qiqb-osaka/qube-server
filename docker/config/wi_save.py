import numpy as np
import json
import os
import traceback

import typer
import sys

# TODO: calibration_sets
# - qubit_with_mt_auto_format.json

def append_sys_path(path):
    if not path in sys.path:
        sys.path.append(path)
    else:    
        print(f"Skipped: {path} is already in sys.path.", file=sys.stderr)

append_sys_path("../lib/")
append_sys_path("../lib/measurement_tool_orion")
append_sys_path("../lib/measurement_tool_orion_automation")
append_sys_path("./lib/")
#../../../../meas/labrad-test/
# append_sys_path("../../../../meas/labrad-test/")
# append_sys_path("../../../../meas/labrad-test/measurement_tool_orion")
# append_sys_path("../../../../meas/labrad-test/measurement_tool_orion_automation")
# append_sys_path("./lib/")

from measurement_tool.units import *
from measurement_tool import Session
from measurement_tool.datataking.qube.time_domain import TimeDomainInstrumentManager as TDM
from measurement_tool import CalibrationNote

app = typer.Typer()

@app.command()
def main(
    path: str = typer.Option("./"),
    suffix: str = typer.Option(""),
    # full / calib / recalib
    mode: str = typer.Option("calib"),
    savefig: bool = typer.Option(True, '+wi/-wi'),
) -> None:
    
    session = Session(
        #labrad_hostname = "host.docker.internal", 
        #labrad_hostname = "172.17.0.1",
        #labrad_hostname = "gateway.docker.internal",
        #labrad_hostname = "172.27.99.35",
        #labrad_hostname = "localhost", 
        labrad_username = "",
        labrad_password = "Cooper2e",
        #labrad_password = "",
        cooling_down_id = "CD26",
        experiment_username = "cloud",
        package_name = "Al64Q1",
    )
    
    with open("wiring_info.json") as fin:
        wiring_info = json.load(fin)
        session.save_wiring_info("XLD2_current", wiring_info)

if __name__ == "__main__":
    app()
