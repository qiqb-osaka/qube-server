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
    "control": {
        "Q0": {
            "device_id": "quel1se-1-09-control_7"
        },
        "Q1": {
            "device_id": "quel1se-1-09-control_6"
        },
        "Q2": {
            "device_id": "quel1se-1-09-control_9"
        },
        "Q3": {
            "device_id": "quel1se-1-09-control_8"
        },
        "Q4": {
            "device_id": "quel1se-1-04-control_7"
        },
        "Q5": {
            "device_id": "quel1se-1-04-control_6"
        },
        "Q6": {
            "device_id": "quel1se-1-04-control_9"
        },
        "Q7": {
            "device_id": "quel1se-1-04-control_8"
        },
        "Q8": {
            "device_id": "quel1se-1-18-control_7"
        },
        "Q9": {
            "device_id": "quel1se-1-18-control_6"
        },
        "Q10": {
            "device_id": "quel1se-1-18-control_9"
        },
        "Q11": {
            "device_id": "quel1se-1-18-control_8"
        },
        "Q12": {
            "device_id": "quel1se-1-01-control_7"
        },
        "Q13": {
            "device_id": "quel1se-1-01-control_6"
        },
        "Q14": {
            "device_id": "quel1se-1-01-control_9"
        },
        "Q15": {
            "device_id": "quel1se-1-01-control_8"
        },
        "Q16": {
            "device_id": "quel1se-1-15-control_7"
        },
        "Q17": {
            "device_id": "quel1se-1-15-control_6"
        },
        "Q18": {
            "device_id": "quel1se-1-15-control_9"
        },
        "Q19": {
            "device_id": "quel1se-1-15-control_8"
        },
        "Q20": {
            "device_id": "quel1se-1-10-control_7"
        },
        "Q21": {
            "device_id": "quel1se-1-10-control_6"
        },
        "Q22": {
            "device_id": "quel1se-1-10-control_9"
        },
        "Q23": {
            "device_id": "quel1se-1-10-control_8"
        },
        "Q24": {
            "device_id": "quel1se-1-08-control_7"
        },
        "Q25": {
            "device_id": "quel1se-1-08-control_6"
        },
        "Q26": {
            "device_id": "quel1se-1-08-control_9"
        },
        "Q27": {
            "device_id": "quel1se-1-08-control_8"
        },
        "Q28": {
            "device_id": "quel1se-1-05-control_7"
        },
        "Q29": {
            "device_id": "quel1se-1-05-control_6"
        },
        "Q30": {
            "device_id": "quel1se-1-05-control_9"
        },
        "Q31": {
            "device_id": "quel1se-1-05-control_8"
        },
        "Q32": {
            "device_id": "quel1se-1-17-control_7"
        },
        "Q33": {
            "device_id": "quel1se-1-17-control_6"
        },
        "Q34": {
            "device_id": "quel1se-1-17-control_9"
        },
        "Q35": {
            "device_id": "quel1se-1-17-control_8"
        },
        "Q36": {
            "device_id": "quel1se-1-02-control_7"
        },
        "Q37": {
            "device_id": "quel1se-1-02-control_6"
        },
        "Q38": {
            "device_id": "quel1se-1-02-control_9"
        },
        "Q39": {
            "device_id": "quel1se-1-02-control_8"
        },
        "Q40": {
            "device_id": "quel1se-1-14-control_7"
        },
        "Q41": {
            "device_id": "quel1se-1-14-control_6"
        },
        "Q42": {
            "device_id": "quel1se-1-14-control_9"
        },
        "Q43": {
            "device_id": "quel1se-1-14-control_8"
        },
        "Q44": {
            "device_id": "quel1se-1-11-control_7"
        },
        "Q45": {
            "device_id": "quel1se-1-11-control_6"
        },
        "Q46": {
            "device_id": "quel1se-1-11-control_9"
        },
        "Q47": {
            "device_id": "quel1se-1-11-control_8"
        },
        "Q48": {
            "device_id": "quel1se-1-07-control_7"
        },
        "Q49": {
            "device_id": "quel1se-1-07-control_6"
        },
        "Q50": {
            "device_id": "quel1se-1-07-control_9"
        },
        "Q51": {
            "device_id": "quel1se-1-07-control_8"
        },
        "Q52": {
            "device_id": "quel1se-1-06-control_7"
        },
        "Q53": {
            "device_id": "quel1se-1-06-control_6"
        },
        "Q54": {
            "device_id": "quel1se-1-06-control_9"
        },
        "Q55": {
            "device_id": "quel1se-1-06-control_8"
        },
        "Q56": {
            "device_id": "quel1se-1-16-control_7"
        },
        "Q57": {
            "device_id": "quel1se-1-16-control_6"
        },
        "Q58": {
            "device_id": "quel1se-1-16-control_9"
        },
        "Q59": {
            "device_id": "quel1se-1-16-control_8"
        },
        "Q60": {
            "device_id": "quel1se-1-03-control_7"
        },
        "Q61": {
            "device_id": "quel1se-1-03-control_6"
        },
        "Q62": {
            "device_id": "quel1se-1-03-control_9"
        },
        "Q63": {
            "device_id": "quel1se-1-03-control_8"
        },
        "Q64": {
            "device_id": "quel1se-1-13-control_7"
        },
        "Q65": {
            "device_id": "quel1se-1-13-control_6"
        },
        "Q66": {
            "device_id": "quel1se-1-13-control_9"
        },
        "Q67": {
            "device_id": "quel1se-1-13-control_8"
        },
        "Q68": {
            "device_id": "quel1se-1-12-control_7"
        },
        "Q69": {
            "device_id": "quel1se-1-12-control_6"
        },
        "Q70": {
            "device_id": "quel1se-1-12-control_9"
        },
        "Q71": {
            "device_id": "quel1se-1-12-control_8"
        },
        "Q72": {
            "device_id": "quel1se-1-30-control_7"
        },
        "Q73": {
            "device_id": "quel1se-1-30-control_6"
        },
        "Q74": {
            "device_id": "quel1se-1-30-control_9"
        },
        "Q75": {
            "device_id": "quel1se-1-30-control_8"
        },
        "Q76": {
            "device_id": "quel1se-1-31-control_7"
        },
        "Q77": {
            "device_id": "quel1se-1-31-control_6"
        },
        "Q78": {
            "device_id": "quel1se-1-31-control_9"
        },
        "Q79": {
            "device_id": "quel1se-1-31-control_8"
        },
        "Q80": {
            "device_id": "quel1se-1-21-control_7"
        },
        "Q81": {
            "device_id": "quel1se-1-21-control_6"
        },
        "Q82": {
            "device_id": "quel1se-1-21-control_9"
        },
        "Q83": {
            "device_id": "quel1se-1-21-control_8"
        },
        "Q84": {
            "device_id": "quel1se-1-34-control_7"
        },
        "Q85": {
            "device_id": "quel1se-1-34-control_6"
        },
        "Q86": {
            "device_id": "quel1se-1-34-control_9"
        },
        "Q87": {
            "device_id": "quel1se-1-34-control_8"
        },
        "Q88": {
            "device_id": "quel1se-1-24-control_7"
        },
        "Q89": {
            "device_id": "quel1se-1-24-control_6"
        },
        "Q90": {
            "device_id": "quel1se-1-24-control_9"
        },
        "Q91": {
            "device_id": "quel1se-1-24-control_8"
        },
        "Q92": {
            "device_id": "quel1se-1-25-control_7"
        },
        "Q93": {
            "device_id": "quel1se-1-25-control_6"
        },
        "Q94": {
            "device_id": "quel1se-1-25-control_9"
        },
        "Q95": {
            "device_id": "quel1se-1-25-control_8"
        },
        "Q96": {
            "device_id": "quel1se-1-29-control_7"
        },
        "Q97": {
            "device_id": "quel1se-1-29-control_6"
        },
        "Q98": {
            "device_id": "quel1se-1-29-control_9"
        },
        "Q99": {
            "device_id": "quel1se-1-29-control_8"
        },
        "Q100": {
            "device_id": "quel1se-1-32-control_7"
        },
        "Q101": {
            "device_id": "quel1se-1-32-control_6"
        },
        "Q102": {
            "device_id": "quel1se-1-32-control_9"
        },
        "Q103": {
            "device_id": "quel1se-1-32-control_8"
        },
        "Q104": {
            "device_id": "quel1se-1-20-control_7"
        },
        "Q105": {
            "device_id": "quel1se-1-20-control_6"
        },
        "Q106": {
            "device_id": "quel1se-1-20-control_9"
        },
        "Q107": {
            "device_id": "quel1se-1-20-control_8"
        },
        "Q108": {
            "device_id": "quel1se-1-35-control_7"
        },
        "Q109": {
            "device_id": "quel1se-1-35-control_6"
        },
        "Q110": {
            "device_id": "quel1se-1-35-control_9"
        },
        "Q111": {
            "device_id": "quel1se-1-35-control_8"
        },
        "Q112": {
            "device_id": "quel1se-1-23-control_7"
        },
        "Q113": {
            "device_id": "quel1se-1-23-control_6"
        },
        "Q114": {
            "device_id": "quel1se-1-23-control_9"
        },
        "Q115": {
            "device_id": "quel1se-1-23-control_8"
        },
        "Q116": {
            "device_id": "quel1se-1-26-control_7"
        },
        "Q117": {
            "device_id": "quel1se-1-26-control_6"
        },
        "Q118": {
            "device_id": "quel1se-1-26-control_9"
        },
        "Q119": {
            "device_id": "quel1se-1-26-control_8"
        },
        "Q120": {
            "device_id": "quel1se-1-28-control_7"
        },
        "Q121": {
            "device_id": "quel1se-1-28-control_6"
        },
        "Q122": {
            "device_id": "quel1se-1-28-control_9"
        },
        "Q123": {
            "device_id": "quel1se-1-28-control_8"
        },
        "Q124": {
            "device_id": "quel1se-1-33-control_7"
        },
        "Q125": {
            "device_id": "quel1se-1-33-control_6"
        },
        "Q126": {
            "device_id": "quel1se-1-33-control_9"
        },
        "Q127": {
            "device_id": "quel1se-1-33-control_8"
        },
        "Q128": {
            "device_id": "quel1se-1-19-control_7"
        },
        "Q129": {
            "device_id": "quel1se-1-19-control_6"
        },
        "Q130": {
            "device_id": "quel1se-1-19-control_9"
        },
        "Q131": {
            "device_id": "quel1se-1-19-control_8"
        },
        "Q132": {
            "device_id": "quel1se-1-36-control_7"
        },
        "Q133": {
            "device_id": "quel1se-1-36-control_6"
        },
        "Q134": {
            "device_id": "quel1se-1-36-control_9"
        },
        "Q135": {
            "device_id": "quel1se-1-36-control_8"
        },
        "Q136": {
            "device_id": "quel1se-1-22-control_7"
        },
        "Q137": {
            "device_id": "quel1se-1-22-control_6"
        },
        "Q138": {
            "device_id": "quel1se-1-22-control_9"
        },
        "Q139": {
            "device_id": "quel1se-1-22-control_8"
        },
        "Q140": {
            "device_id": "quel1se-1-27-control_7"
        },
        "Q141": {
            "device_id": "quel1se-1-27-control_6"
        },
        "Q142": {
            "device_id": "quel1se-1-27-control_9"
        },
        "Q143": {
            "device_id": "quel1se-1-27-control_8"
        }
    },
    "readout": {
        "M0": {
            "device_id": "quel1se-1-09-readout_1"
        },
        "M1": {
            "device_id": "quel1se-1-04-readout_1"
        },
        "M2": {
            "device_id": "quel1se-1-18-readout_1"
        },
        "M3": {
            "device_id": "quel1se-1-01-readout_1"
        },
        "M4": {
            "device_id": "quel1se-1-15-readout_1"
        },
        "M5": {
            "device_id": "quel1se-1-10-readout_1"
        },
        "M6": {
            "device_id": "quel1se-1-08-readout_1"
        },
        "M7": {
            "device_id": "quel1se-1-05-readout_1"
        },
        "M8": {
            "device_id": "quel1se-1-17-readout_1"
        },
        "M9": {
            "device_id": "quel1se-1-02-readout_1"
        },
        "M10": {
            "device_id": "quel1se-1-14-readout_1"
        },
        "M11": {
            "device_id": "quel1se-1-11-readout_1"
        },
        "M12": {
            "device_id": "quel1se-1-07-readout_1"
        },
        "M13": {
            "device_id": "quel1se-1-06-readout_1"
        },
        "M14": {
            "device_id": "quel1se-1-16-readout_1"
        },
        "M15": {
            "device_id": "quel1se-1-03-readout_1"
        },
        "M16": {
            "device_id": "quel1se-1-13-readout_1"
        },
        "M17": {
            "device_id": "quel1se-1-12-readout_1"
        },
        "M18": {
            "device_id": "quel1se-1-30-readout_1"
        },
        "M19": {
            "device_id": "quel1se-1-31-readout_1"
        },
        "M20": {
            "device_id": "quel1se-1-21-readout_1"
        },
        "M21": {
            "device_id": "quel1se-1-34-readout_1"
        },
        "M22": {
            "device_id": "quel1se-1-24-readout_1"
        },
        "M23": {
            "device_id": "quel1se-1-25-readout_1"
        },
        "M24": {
            "device_id": "quel1se-1-29-readout_1"
        },
        "M25": {
            "device_id": "quel1se-1-32-readout_1"
        },
        "M26": {
            "device_id": "quel1se-1-20-readout_1"
        },
        "M27": {
            "device_id": "quel1se-1-35-readout_1"
        },
        "M28": {
            "device_id": "quel1se-1-23-readout_1"
        },
        "M29": {
            "device_id": "quel1se-1-26-readout_1"
        },
        "M30": {
            "device_id": "quel1se-1-28-readout_1"
        },
        "M31": {
            "device_id": "quel1se-1-33-readout_1"
        },
        "M32": {
            "device_id": "quel1se-1-19-readout_1"
        },
        "M33": {
            "device_id": "quel1se-1-36-readout_1"
        },
        "M34": {
            "device_id": "quel1se-1-22-readout_1"
        },
        "M35": {
            "device_id": "quel1se-1-27-readout_1"
        }
    },
    "pump": {
        "M0": {
            "device_id": "quel1se-1-09-pump_2"
        },
        "M1": {
            "device_id": "quel1se-1-04-pump_2"
        },
        "M2": {
            "device_id": "quel1se-1-18-pump_2"
        },
        "M3": {
            "device_id": "quel1se-1-01-pump_2"
        },
        "M4": {
            "device_id": "quel1se-1-15-pump_2"
        },
        "M5": {
            "device_id": "quel1se-1-10-pump_2"
        },
        "M6": {
            "device_id": "quel1se-1-08-pump_2"
        },
        "M7": {
            "device_id": "quel1se-1-05-pump_2"
        },
        "M8": {
            "device_id": "quel1se-1-17-pump_2"
        },
        "M9": {
            "device_id": "quel1se-1-02-pump_2"
        },
        "M10": {
            "device_id": "quel1se-1-14-pump_2"
        },
        "M11": {
            "device_id": "quel1se-1-11-pump_2"
        },
        "M12": {
            "device_id": "quel1se-1-07-pump_2"
        },
        "M13": {
            "device_id": "quel1se-1-06-pump_2"
        },
        "M14": {
            "device_id": "quel1se-1-16-pump_2"
        },
        "M15": {
            "device_id": "quel1se-1-03-pump_2"
        },
        "M16": {
            "device_id": "quel1se-1-13-pump_2"
        },
        "M17": {
            "device_id": "quel1se-1-12-pump_2"
        },
        "M18": {
            "device_id": "quel1se-1-30-pump_2"
        },
        "M19": {
            "device_id": "quel1se-1-31-pump_2"
        },
        "M20": {
            "device_id": "quel1se-1-21-pump_2"
        },
        "M21": {
            "device_id": "quel1se-1-34-pump_2"
        },
        "M22": {
            "device_id": "quel1se-1-24-pump_2"
        },
        "M23": {
            "device_id": "quel1se-1-25-pump_2"
        },
        "M24": {
            "device_id": "quel1se-1-29-pump_2"
        },
        "M25": {
            "device_id": "quel1se-1-32-pump_2"
        },
        "M26": {
            "device_id": "quel1se-1-20-pump_2"
        },
        "M27": {
            "device_id": "quel1se-1-35-pump_2"
        },
        "M28": {
            "device_id": "quel1se-1-23-pump_2"
        },
        "M29": {
            "device_id": "quel1se-1-26-pump_2"
        },
        "M30": {
            "device_id": "quel1se-1-28-pump_2"
        },
        "M31": {
            "device_id": "quel1se-1-33-pump_2"
        },
        "M32": {
            "device_id": "quel1se-1-19-pump_2"
        },
        "M33": {
            "device_id": "quel1se-1-36-pump_2"
        },
        "M34": {
            "device_id": "quel1se-1-22-pump_2"
        },
        "M35": {
            "device_id": "quel1se-1-27-pump_2"
        }
    }
}
    
    session.save_wiring_info("XLD3_current", wiring_info)
    #print(wiring_info)


if __name__ == "__main__":
    app()
