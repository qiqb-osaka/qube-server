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
        labrad_hostname = "localhost", 
        labrad_username = "",
        #labrad_password = "",
        labrad_password = "",
        cooling_down_id = "CD26",
        experiment_username = "cloud",
        package_name = "Al64Q1",
    )
    
    wiring_info = {
        'control': {
            'Q16': {'device_id': 'riken1-01-control_5'},
            'Q17': {'device_id': 'riken1-01-control_6'},
            'Q18': {'device_id': 'riken1-01-control_7'},
            'Q19': {'device_id': 'riken1-01-control_8'},
            'Q20': {'device_id': 'ou1-02-control_5'},
            'Q21': {'device_id': 'ou1-02-control_6'},
            'Q22': {'device_id': 'ou1-02-control_7'},
            'Q23': {'device_id': 'ou1-02-control_8'},
            'Q36': {'device_id': 'ou3-01-control_5'},
            'Q37': {'device_id': 'ou3-01-control_6'},
            'Q38': {'device_id': 'ou3-01-control_7'},
            'Q39': {'device_id': 'ou3-01-control_8'},
            'Q52': {'device_id': 'Quel-1_5-01-control_5'},
            'Q53': {'device_id': 'Quel-1_5-01-control_6'},
            'Q54': {'device_id': 'Quel-1_5-01-control_7'},
            'Q55': {'device_id': 'Quel-1_5-01-control_8'},
            'Q60': {'device_id': 'riken1-10-control_5'},
            'Q61': {'device_id': 'riken1-10-control_6'},
            'Q62': {'device_id': 'riken1-10-control_7'},
            'Q63': {'device_id': 'riken1-10-control_8'},
        },
        "readout": {
            "M4": {
                "device_id": "riken1-01-readout_01"
            },
            "M5": {
                "device_id": "ou1-02-readout_01"
            },
            "M9": {
                "device_id": "ou3-01-readout_01"
            },
            "M13": {
                "device_id": "Quel-1_5-01-readout_01"
            },
            "M15": {
                "device_id": "riken1-10-readout_01"
            }
        }
    }
    
    session.save_wiring_info("XLD_current", wiring_info)
    #print(wiring_info)


if __name__ == "__main__":
    app()
