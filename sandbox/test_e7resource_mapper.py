from quel_ic_config import Quel1Box, Quel1BoxType
from quel_ic_config.e7resource_mapper import Quel1E7ResourceMapper

box = Quel1Box.create(
    ipaddr_wss="10.1.0.31",
    boxtype=Quel1BoxType.QuBE_OU_TypeA,
)

rmap = Quel1E7ResourceMapper(box.css, box.wss)
print(rmap)
