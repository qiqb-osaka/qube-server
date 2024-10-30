from quel_ic_config import Quel1Box, Quel1BoxType
from quel_ic_config.e7resource_mapper import Quel1E7ResourceMapper

box = Quel1Box.create(
    ipaddr_wss="10.1.0.31",
    boxtype=Quel1BoxType.QuBE_OU_TypeA,
)

group, line = 0, 0

rmap = Quel1E7ResourceMapper(box.css, box.wss)
#print(rmap)
channels = box._dev.get_channels_of_line(group, line)
print("channels: ", channels)
channel = channels[0]
aws_ch = rmap.get_awg_of_channel(group, line, channel)
print("aws_ch: ", aws_ch)
