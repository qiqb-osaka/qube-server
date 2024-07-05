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
        labrad_password = "Cooper2e",
        #labrad_password = "",
        cooling_down_id = "CD26",
        experiment_username = "cloud",
        package_name = "Al64Q1",
    )
    
    wiring_info = {
    "bias": {
        "M0": {
            "device_id": "Qblox1-10"
        },
        "M1": {
            "device_id": "Qblox1-12"
        },
        "M10": {
            "device_id": "Qblox1-6"
        },
        "M11": {
            "device_id": "Qblox1-8"
        },
        "M12": {
            "device_id": "Qblox1-11"
        },
        "M13": {
            "device_id": "Qblox1-9"
        },
        "M14": {
            "device_id": "Qblox1-2"
        },
        "M15": {
            "device_id": "Qblox1-4"
        },
        "M2": {
            "device_id": "Qblox1-3"
        },
        "M3": {
            "device_id": "Qblox1-1"
        },
        "M4": {
            "device_id": "Qblox1-14"
        },
        "M5": {
            "device_id": "Qblox1-16"
        },
        "M6": {
            "device_id": "Qblox1-7"
        },
        "M7": {
            "device_id": "Qblox1-5"
        },
        "M8": {
            "device_id": "Qblox1-15"
        },
        "M9": {
            "device_id": "Qblox1-13"
        }
    },
    "control": {
        "Q0": {
            "device_id": "qube007-control_5"
        },
        "Q1": {
            "device_id": "qube007-control_6"
        },
        "Q10": {
            "device_id": "qube001-control_7"
        },
        "Q11": {
            "device_id": "qube001-control_8"
        },
        "Q12": {
            "device_id": "qube002-control_5"
        },
        "Q13": {
            "device_id": "qube002-control_6"
        },
        "Q14": {
            "device_id": "qube002-control_7"
        },
        "Q15": {
            "device_id": "qube002-control_8"
        },
        "Q16": {
            "device_id": "qube009-control_5"
        },
        "Q17": {
            "device_id": "qube009-control_2"
        },
        "Q18": {
            "device_id": "qube009-control_0"
        },
        "Q19": {
            "device_id": "qube009-control_6"
        },
        "Q2": {
            "device_id": "qube007-control_7"
        },
        "Q20": {
            "device_id": "qube009-control_7"
        },
        "Q21": {
            "device_id": "qube009-control_d"
        },
        "Q22": {
            "device_id": "qube009-control_b"
        },
        "Q23": {
            "device_id": "qube009-control_8"
        },
        "Q24": {
            "device_id": "qube003-control_5"
        },
        "Q25": {
            "device_id": "qube003-control_2"
        },
        "Q26": {
            "device_id": "qube003-control_0"
        },
        "Q27": {
            "device_id": "qube003-control_6"
        },
        "Q28": {
            "device_id": "qube003-control_7"
        },
        "Q29": {
            "device_id": "qube003-control_d"
        },
        "Q3": {
            "device_id": "qube007-control_8"
        },
        "Q30": {
            "device_id": "qube003-control_b"
        },
        "Q31": {
            "device_id": "qube003-control_8"
        },
        "Q32": {
            "device_id": "qube010-control_5"
        },
        "Q33": {
            "device_id": "qube010-control_6"
        },
        "Q34": {
            "device_id": "qube010-control_7"
        },
        "Q35": {
            "device_id": "qube010-control_8"
        },
        "Q36": {
            "device_id": "qube011-control_5"
        },
        "Q37": {
            "device_id": "qube011-control_6"
        },
        "Q38": {
            "device_id": "qube011-control_7"
        },
        "Q39": {
            "device_id": "qube011-control_8"
        },
        "Q4": {
            "device_id": "qube008-control_5"
        },
        "Q40": {
            "device_id": "qube004-control_5"
        },
        "Q41": {
            "device_id": "qube004-control_6"
        },
        "Q42": {
            "device_id": "qube004-control_7"
        },
        "Q43": {
            "device_id": "qube004-control_8"
        },
        "Q44": {
            "device_id": "qube005-control_5"
        },
        "Q45": {
            "device_id": "qube005-control_6"
        },
        "Q46": {
            "device_id": "qube005-control_7"
        },
        "Q47": {
            "device_id": "qube005-control_8"
        },
        "Q48": {
            "device_id": "qube012-control_5"
        },
        "Q49": {
            "device_id": "qube012-control_2"
        },
        "Q5": {
            "device_id": "qube008-control_6"
        },
        "Q50": {
            "device_id": "qube012-control_0"
        },
        "Q51": {
            "device_id": "qube012-control_6"
        },
        "Q52": {
            "device_id": "qube012-control_7"
        },
        "Q53": {
            "device_id": "qube012-control_d"
        },
        "Q54": {
            "device_id": "qube012-control_b"
        },
        "Q55": {
            "device_id": "qube012-control_8"
        },
        "Q56": {
            "device_id": "qube006-control_5"
        },
        "Q57": {
            "device_id": "qube006-control_2"
        },
        "Q58": {
            "device_id": "qube006-control_0"
        },
        "Q59": {
            "device_id": "qube006-control_6"
        },
        "Q6": {
            "device_id": "qube008-control_7"
        },
        "Q60": {
            "device_id": "qube006-control_7"
        },
        "Q61": {
            "device_id": "qube006-control_d"
        },
        "Q62": {
            "device_id": "qube006-control_b"
        },
        "Q63": {
            "device_id": "qube006-control_8"
        },
        "Q7": {
            "device_id": "qube008-control_8"
        },
        "Q8": {
            "device_id": "qube001-control_5"
        },
        "Q9": {
            "device_id": "qube001-control_6"
        }
    },
    "pump": {
        "M0": {
            "device_id": "qube007-pump_2"
        },
        "M1": {
            "device_id": "qube008-pump_2"
        },
        "M10": {
            "device_id": "qube004-pump_2"
        },
        "M11": {
            "device_id": "qube005-pump_2"
        },
        "M12": {
            "device_id": "qube010-pump_b"
        },
        "M13": {
            "device_id": "qube011-pump_b"
        },
        "M14": {
            "device_id": "qube004-pump_b"
        },
        "M15": {
            "device_id": "qube005-pump_b"
        },
        "M2": {
            "device_id": "qube001-pump_2"
        },
        "M3": {
            "device_id": "qube002-pump_2"
        },
        "M4": {
            "device_id": "qube007-pump_b"
        },
        "M5": {
            "device_id": "qube008-pump_b"
        },
        "M6": {
            "device_id": "qube001-pump_b"
        },
        "M7": {
            "device_id": "qube002-pump_b"
        },
        "M8": {
            "device_id": "qube010-pump_2"
        },
        "M9": {
            "device_id": "qube011-pump_2"
        }
    },
    "readout": {
        "M0": {
            "device_id": "qube007-readout_01"
        },
        "M1": {
            "device_id": "qube008-readout_01"
        },
        "M10": {
            "device_id": "qube004-readout_01"
        },
        "M11": {
            "device_id": "qube005-readout_01"
        },
        "M12": {
            "device_id": "qube010-readout_cd"
        },
        "M13": {
            "device_id": "qube011-readout_cd"
        },
        "M14": {
            "device_id": "qube004-readout_cd"
        },
        "M15": {
            "device_id": "qube005-readout_cd"
        },
        "M2": {
            "device_id": "qube001-readout_01"
        },
        "M3": {
            "device_id": "qube002-readout_01"
        },
        "M4": {
            "device_id": "qube007-readout_cd"
        },
        "M5": {
            "device_id": "qube008-readout_cd"
        },
        "M6": {
            "device_id": "qube001-readout_cd"
        },
        "M7": {
            "device_id": "qube002-readout_cd"
        },
        "M8": {
            "device_id": "qube010-readout_01"
        },
        "M9": {
            "device_id": "qube011-readout_01"
        }
    }
}
    
    session.save_wiring_info("XLD2_current", wiring_info)
    #print(wiring_info)


if __name__ == "__main__":
    app()
