import sys
import json
import concurrent

import numpy as np

from labrad import types as T
from labrad.devices import DeviceServer
from labrad.server import setting
from labrad.units import Value
from labrad.concurrent import future_to_deferred
from twisted.internet.defer import inlineCallbacks, returnValue


from e7awgsw import (
    AwgCtrl,
    AWG,
    CaptureModule,
)
from quel_clock_master import (
    QuBEMasterClient,
    SequencerClient,
)  # for multi-sync operation
import qubelsi.qube

from quel_ic_config import Quel1BoxType

from constants import QSConstants, QSMessage
from devices import QuBE_ReadoutLine, QuBE_ControlLine, QuBE_ReadoutLine_debug_otasuke, QuBE_ControlLine_debug_otasuke
from utils import pingger, QuBECaptureCtrl

############################################################
#
# QUBE SERVER
#


class QuBE_Server(DeviceServer):
    name = QSConstants.SRVNAME
    deviceWrappers = {
        QSConstants.CNL_READ_VAL: QuBE_ReadoutLine,
        QSConstants.CNL_CTRL_VAL: QuBE_ControlLine,
    }
    possibleLinks = {}
    chassisSkew = {}
    adi_api_path = None

    @inlineCallbacks
    def initServer(self):  # @inlineCallbacks
        yield DeviceServer.initServer(self)

        cxn = self.client
        reg = cxn[QSConstants.REGSRV]
        try:
            yield reg.cd(QSConstants.REGDIR)
            config = yield reg.get(QSConstants.REGLNK)
            self.possibleLinks = json.loads(config)
            skew = yield reg.get(QSConstants.REGSKEW)
            self.chassisSkew = json.loads(skew)
            self.master_link = yield reg.get(QSConstants.REGMASTERLNK)
            self.adi_api_path = yield reg.get(QSConstants.REGAPIPATH)
            self._master_ctrl = yield QuBEMasterClient(
                self.master_link, receiver_limit_by_bind=True
            )
            self._sync_ctrl = dict()
            self.__is_clock_opened = True
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)

        try:
            max_workers = QSConstants.THREAD_MAX_WORKERS
            self._thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            )  # for a threaded operation
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)

    def initContext(self, c):
        DeviceServer.initContext(self, c)
        c[QSConstants.DAC_CNXT_TAG] = dict()
        c[QSConstants.ACQ_CNXT_TAG] = dict()
        c[QSConstants.DAQ_TOUT_TAG] = QSConstants.DAQ_INITTOUT
        c[QSConstants.DAQ_SDLY_TAG] = QSConstants.DAQ_INITSDLY

    def chooseDeviceWrapper(self, *args, **kw):
        tag = (
            QSConstants.CNL_READ_VAL
            if QSConstants.CNL_READ_VAL in args[2]
            else QSConstants.CNL_CTRL_VAL
        )
        return self.deviceWrappers[tag]

    # 例：QuEL-1 Type-A の場合
    # | MxFEの番号 | DAC番号 | (group, line)　 | ポート番号 | 機能 |
    # |-----------|--------|----------------|-------|------|
    # | 0       | 0     | (0, 0)         | 1     | Read-out |
    # | 0       | 1     | (0, 1)         | 3     | Pump |
    # | 0       | 2     | (0, 2)         | 2     | Ctrl |
    # | 0       | 3     | (0, 3)         | 4     | Ctrl |
    # | 1       | 3     | (1, 0)         | 8     | Read-out |
    # | 1       | 2     | (1, 1)         | 10    | Pump |
    # | 1       | 1     | (1, 2)         | 11    | Ctrl |
    # | 1       | 0     | (1, 3)         | 9     | Ctrl |

    # 例：Quel-1 Type-B の場合
    # | MxFEの番号 | DAC番号 | (group, line)　 | ポート番号 | 機能   |
    # |-----------|--------|----------------|-------|------|
    # | 0       | 0     | (0, 0)         | 1     | Ctrl |
    # | 0       | 1     | (0, 1)         | 2     | Ctrl |
    # | 0       | 2     | (0, 2)         | 3     | Ctrl |
    # | 0       | 3     | (0, 3)         | 4     | Ctrl |
    # | 1       | 3     | (1, 0)         | 8     | Ctrl |
    # | 1       | 2     | (1, 1)         | 9     | Ctrl |
    # | 1       | 1     | (1, 2)         | 11    | Ctrl |
    # | 1       | 0     | (1, 3)         | 10    | Ctrl |
    # おそらくtype:Bの場合、全部これ

    # 例: QuBE の場合
    # | MxFEの番号 | DAC番号 | (group, line)　 | ポート番号 | Type-A機能 | Type-B 機能 |
    # |-----------|--------|----------------|-------|----------|-----------|
    # | 0       | 0     | (0, 0)         | 0     | Read-out | Ctrl      |
    # | 0       | 1     | (0, 1)         | 2     | Pump     | Ctrl      |
    # | 0       | 2     | (0, 2)         | 5     | Ctrl     | Ctrl      |
    # | 0       | 3     | (0, 3)         | 6     | Ctrl     | Ctrl      |
    # | 1       | 3     | (1, 0)         | 13    | Read-out | Ctrl      |
    # | 1       | 2     | (1, 1)         | 11    | Pump     | Ctrl      |
    # | 1       | 1     | (1, 2)         | 8     | Ctrl     | Ctrl      |
    # | 1       | 0     | (1, 3)         | 7     | Ctrl     | Ctrl      |

    # ADC用のrlineとrunit
    # | ポート番号 | 受信LO番号 | MxFEの番号 | ADC番号, CNCO番号, FNCO番号 | (group, rline, runit)　 | キャプチャモジュール | キャプチャユニット |
    # |----|---|---|---------|------------------------|----|---|
    # | 0  | 0 | 0 | 3, 3, 5 | (0, r, 0)              | 1  | 4 |
    # | 0  | 0 | 0 | 3, 3, 5 | (0, r, 1)              | 1  | 5 |
    # | 0  | 0 | 0 | 3, 3, 5 | (0, r, 2)              | 1  | 6 |
    # | 0  | 0 | 0 | 3, 3, 5 | (0, r, 3)              | 1  | 7 |
    # | 5  | 1 | 0 | 2, 2, 4 | (0, m, 0)              | 1  | 4 |
    # | 5  | 1 | 0 | 2, 2, 4 | (0, m, 1)              | 1  | 5 |
    # | 5  | 1 | 0 | 2, 2, 4 | (0, m, 2)              | 1  | 6 |
    # | 5  | 1 | 0 | 2, 2, 4 | (0, m, 3)              | 1  | 7 |
    # | 7  | 7 | 1 | 3, 3, 5 | (0, r, 0)              | 0  | 0 |
    # | 7  | 7 | 1 | 3, 3, 5 | (0, r, 1)              | 0  | 1 |
    # | 7  | 7 | 1 | 3, 3, 5 | (0, r, 2)              | 0  | 2 |
    # | 7  | 7 | 1 | 3, 3, 5 | (0, r, 3)              | 0  | 3 |
    # | 12 | 6 | 1 | 2, 2, 4 | (0, m, 0)              | 0  | 0 |
    # | 12 | 6 | 1 | 2, 2, 4 | (0, m, 1)              | 0  | 1 |
    # | 12 | 6 | 1 | 2, 2, 4 | (0, m, 2)              | 0  | 2 |
    # | 12 | 6 | 1 | 2, 2, 4 | (0, m, 3)              | 0  | 3 |


    # TODO: とりあえずコンバートテーブルを作るが後でPossibleLinksで登録する
    def convert_device_type_for_quelware(self, name, type) -> Quel1BoxType:
        if "ou" in name:
            if type == "A":
                return Quel1BoxType.QuBE_OU_TypeA
            elif type == "B":
                return Quel1BoxType.QuBE_OU_TypeB
            else:
                return None
        elif "riken" in name:
            if type == "A":
                return Quel1BoxType.QuBE_RIKEN_TypeA
            elif type == "B":
                return Quel1BoxType.QuBE_RIKEN_TypeB
            else:
                return None
        # TODO: 名前がQuel-1だが、Port配置はQuBEと同じになっている模様。
        elif "Quel-1" in name:
            if type == "A":
                return Quel1BoxType.QuBE_OU_TypeA
            elif type == "B":
                return Quel1BoxType.QuBE_OU_TypeB
            else:
                return None
        elif "Quel" in name:
            if type == "A":
                return Quel1BoxType.QuEL1_TypeA
            elif type == "B":
                return Quel1BoxType.QuEL1_TypeB
            else:
                return None
        return None

    # TODO: PossibleLinksで登録するようになったらこれも不要
    def get_dac_port_from_name(self, name):
        # 名前の後ろにポート番号がつく（16進数なので注意）
        # readout_cdの場合は、13
        # a: 10
        # b: 11
        # c: 12
        # d: 13
        #print("name:", name)
        idx = name.rfind("_")
        try:
            port = name[idx + 1:]
            # TODO: debug
            #print("port:", port)
            if port == "01":
                # 0がDACのポートで、1がADCのポート
                return 0
            elif port == "cd":
                # d:13がDACのポートで、c:12がADCのポート
                return 13
            elif port == "a":
                return 10
            elif port == "b":
                return 11
            return int(port)
        except Exception:
            return -1

    # TODO: PossibleLinksで登録するようになったらこれも不要
    def get_adc_rline_from_name(self, name):
        idx = name.rfind("_")
        try:
            port = name[idx + 1:]
            if port == "01":
                # 0がDACのポートで、1がADCのポート
                return "r"
            elif port == "cd":
                # d:13がDACのポートで、c:12がADCのポート
                return "m"
            return ""
        except Exception:
            return ""

    # TODO: とりあえずコンバートテーブルを作るが後でPossibleLinksで登録する
    def convert_device_group_and_line(self, name, type):
        # TODO: QuEL-1 Type-Aは放置
        matrix_a = {0:(0,0), 2:(0,1), 5:(0,2), 6:(0,3), 13:(1,0), 11:(1,1), 8:(1,2), 7:(1,3)}
        matrix_b = {1:(0,0), 2:(0,1), 3:(0,2), 4:(0,3), 8:(1,0), 9:(1,1), 11:(1,2), 10:(1,3)}
        port = self.get_dac_port_from_name(name)
        # TODO: debug
        # print("port:", port)
        # print("type:", type)
        if type == "B":
            return matrix_b.get(port)
        else:
            # TODO: QuEL-1 Type-Aは放置
            return matrix_a.get(port)

    def instantiateChannel(self, name, channels, awg_ctrl, cap_ctrl, lsi_ctrl, info):
        def gen_awg(name, role, chassis, channel, awg_ctrl, cap_ctrl, lsi_ctrl):
            awg_ch_ids = channel["ch_dac"]
            cnco_id = channel["cnco_dac"]
            fnco_id = channel["fnco_dac"]
            lo_id = channel["lo_dac"]
            mix_id = channel[QSConstants.CNL_MIXCH_TAG]
            mix_sb = channel[QSConstants.CNL_MIXSB_TAG]
            nco_device = lsi_ctrl.ad9082[cnco_id[0]]
            lo_device = lsi_ctrl.lmx2594[lo_id]
            mix_device = lsi_ctrl.adrf6780[mix_id]
            ipfpga = info[QSConstants.SRV_IPFPGA_TAG]
            iplsi = info[QSConstants.SRV_IPLSI_TAG]
            ipsync = info[QSConstants.SRV_IPCLK_TAG]
            # # TODO: debug
            # print("name:", name)
            # print("channel:", channel)
            # print("channel:name:", channel[QSConstants.CNL_NAME_TAG])
            device_type = self.convert_device_type_for_quelware(name, info["type"])
            group, line = self.convert_device_group_and_line(channel[QSConstants.CNL_NAME_TAG], info["type"])
            # TODO: debug
            # print("group:", group)
            # print("line:", line)
            rline = self.get_adc_rline_from_name(channel[QSConstants.CNL_NAME_TAG])
            # TODO: simple_boxからportを取得するように変更したい

            args = name, role
            kw = dict(
                awg_ctrl=awg_ctrl,
                awg_ch_ids=awg_ch_ids,
                nco_device=nco_device,
                cnco_id=cnco_id[1],
                fnco_id=[_id for _chip, _id in fnco_id],
                lo_device=lo_device,
                mix_device=mix_device,
                mix_sb=mix_sb,
                chassis=chassis,
                ipfpga=ipfpga,
                iplsi=iplsi,
                ipsync=ipsync,
                device_type=device_type,
                group=group,
                line=line,
                rline=rline,
            )

            return (name, args, kw)

        def gen_mux(name, role, chassis, channel, awg_ctrl, cap_ctrl, lsi_ctrl):
            _name, _args, _kw = gen_awg(
                name, role, chassis, channel, awg_ctrl, cap_ctrl, lsi_ctrl
            )

            cap_mod_id = channel["ch_adc"]
            cdnco_id = channel["cnco_adc"]
            capture_units = CaptureModule.get_units(cap_mod_id)

            kw = dict(
                cap_ctrl=cap_ctrl,
                capture_units=capture_units,
                cap_mod_id=cap_mod_id,
                cdnco_id=cdnco_id[1],
            )
            _kw.update(kw)
            return (_name, _args, _kw)

        devices = []
        for channel in channels:
            channel_type = channel[QSConstants.CNL_TYPE_TAG]
            channel_name = name + "-" + channel[QSConstants.CNL_NAME_TAG]
            args = (
                channel_name,
                channel_type,
                name,
                channel,
                awg_ctrl,
                cap_ctrl,
                lsi_ctrl,
            )
            to_be_added = (
                gen_awg(*args)
                if channel_type == QSConstants.CNL_CTRL_VAL
                else (
                    gen_mux(*args) if channel_type == QSConstants.CNL_READ_VAL else None
                )
            )
            if to_be_added is not None:
                devices.append(to_be_added)
        return devices

    def instantiateQube(self, name, info):
        # TODO: debug
        #print("info:", info)
        try:
            ipfpga = info[QSConstants.SRV_IPFPGA_TAG]
            iplsi = info[QSConstants.SRV_IPLSI_TAG]
            channels = info["channels"]
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)
            return list()

        try:
            awg_ctrl = AwgCtrl(ipfpga)  # AWG CONTROL (e7awgsw)
            cap_ctrl = QuBECaptureCtrl(ipfpga)  # CAP CONTROL (inherited from e7awgsw)
            awg_ctrl.initialize(*AWG.all())
            cap_ctrl.initialize(*CaptureModule.all())
            lsi_ctrl = qubelsi.qube.Qube(
                iplsi, self.adi_api_path
            )  # LSI CONTROL (qubelsi.qube)
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)
            return list()

        try:
            devices = self.instantiateChannel(
                name, channels, awg_ctrl, cap_ctrl, lsi_ctrl, info
            )
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)
            devices = list()
        return devices

    @inlineCallbacks
    def findDevices(self):  # @inlineCallbacks
        cxn = self.client
        found = []

        for name in self.possibleLinks.keys():
            print(QSMessage.CHECKING_QUBEUNIT.format(name))
            try:
                res = pingger(self.possibleLinks[name][QSConstants.SRV_IPFPGA_TAG])
                if 0 == res:
                    res = pingger(self.possibleLinks[name][QSConstants.SRV_IPLSI_TAG])
                if 0 != res:
                    res = pingger(self.possibleLinks[name][QSConstants.SRV_IPCLK_TAG])
                if 0 != res:
                    raise Exception(QSMessage.ERR_HOST_NOTFOUND.format(name))
            except Exception as e:
                print(sys._getframe().f_code.co_name, e)
                continue

            print(QSMessage.CNCTABLE_QUBEUNIT.format(name))
            devices = self.instantiateQube(name, self.possibleLinks[name])
            found.extend(devices)

            sync_ctrl = SequencerClient(
                self.possibleLinks[name][QSConstants.SRV_IPCLK_TAG],
                receiver_limit_by_bind=True,
            )
            self._sync_ctrl.update({name: sync_ctrl})
            yield
            # print(sys._getframe().f_code.co_name,found)
        returnValue(found)

    @setting(10, "Reload Skew", returns=["b"])
    def reload_config_skew(self, c):
        """
        Reload skew adjustment time difference among chassis from the registry.

        Returns:
            success : True if successfuly obtained skew value from the registry
        """
        cxn = self.client
        reg = cxn[QSConstants.REGSRV]
        try:
            skew = yield reg.get(QSConstants.REGSKEW)
            self.chassisSkew = json.loads(skew)
        except Exception as e:
            print(sys._getframe().f_code.co_name, e)
            return False
        return True

    @setting(100, "Shots", num_shots=["w"], returns=["w"])
    def number_of_shots(self, c, num_shots=None):
        """
        Read and write the number of repeated experiments.

        The number of <shots> of an experiment with fixed waveform.

        Args:
            num_shots: w
                The number of repeat in an extire experiments. Used to say "shots"
        Returns:
            num_shots: w
        """
        dev = self.selectedDevice(c)
        if num_shots is not None:
            dev.number_of_shots = num_shots
            return num_shots
        else:
            return dev.number_of_shots

    @setting(101, "Repeat Count", repeat=["w"], returns=["w"])
    def repeat_count(self, c, repeat=None):
        """
        OBSOLETED. Use repetition time instead.

        This is no longer used.

        Args:
            repeat: w
                The number of repeat in an extire experiments. Used to say "shots"
        Returns:
            repeat: w
        """
        raise Exception('obsoleted. use "shots" instead')
        return self.number_of_shots(c, repeat)

    @setting(102, "Repetition Time", reptime=["v[s]"], returns=["v[s]"])
    def repetition_time(self, c, reptime=None):
        """
        Read and write reperition time.

        The repetition time of a single experiments include control/readout waveform
        plus wait (blank, not output) duration.

        Args:
            reptime: v[s]
                10.24us - 1s can be set. The duration must be a multiple of 10.24 us
                to satisty phase coherence.
        Returns:
            reptime: v[s]
        """
        dev = self.selectedDevice(c)
        if reptime is None:
            return T.Value(dev.repetition_time, "ns")
        elif dev.static_check_repetition_time(reptime["ns"]):
            dev.repetition_time = int(round(reptime["ns"]))
            return reptime
        else:
            raise ValueError(
                QSMessage.ERR_REP_SETTING.format(
                    "Sequencer", QSConstants.DAQ_REPT_RESOL
                )
            )

    @setting(103, "DAQ Length", length=["v[s]"], returns=["v[s]"])
    def sequence_length(self, c, length=None):
        """
        Read and write waveform length.

        The waveform length supposed to be identical among all channels. It can be
        different, but we have not done yet.

        Args:
            length: v[s]
                The length of sequence waveforms. The length must be a
                multiple of 128 ns. 0.128ns - 200us can be set.
        Returns:
            length: v[s]
        """
        dev = self.selectedDevice(c)
        if length is None:
            return Value(dev.sequence_length, "ns")
        elif dev.static_check_sequence_length(length["ns"]):
            dev.sequence_length = int(length["ns"] + 0.5)
            return length
        else:
            raise ValueError(
                QSMessage.ERR_REP_SETTING.format(
                    "Sequencer", QSConstants.DAQ_SEQL_RESOL
                )
                + QSMessage.ERR_INVALID_RANG.format(
                    "daq_length", "128 ns", "{} ns".format(QSConstants.DAQ_MAXLEN)
                )
            )

    @setting(105, "DAQ Start", returns=["b"])
    def daq_start(self, c):
        """
        Start data acquisition

        The method name [daq_start()] is for backward compatibility with a former
        version of quantum logic analyzer, and I like it. This method finds trigger
        boards to readout FPGA circuits and give them to the boards. All the
        enabled AWGs and MUXs are supposed to be in the current context [c] through
        [._register_awg_channels()] and [_register_mux_channels()].

        Compared to the previous implementation, this method does not require
        [select_device()] before the call.
        """
        dev = self.selectedDevice(c)

        if (
            QSConstants.CNL_READ_VAL == dev.device_role
        ):  # Set trigger board to capture units
            self._readout_mux_start(c)

        for chassis_name in c[QSConstants.ACQ_CNXT_TAG].keys():
            for _dev, _m, _units in c[QSConstants.ACQ_CNXT_TAG][chassis_name]:
                print(chassis_name, _units)  # DEBUG

        for chassis_name in c[QSConstants.DAC_CNXT_TAG].keys():
            _dev, _awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]
            print(chassis_name, _awgs)  # DEBUG
        return True

    def _readout_mux_start(self, c):
        """
        Find trigger AWG bords in multiple chassis

        For each QuBE chassis, we have to select trigger AWG from the AWGs involved
        in the operation. For each QuBE readout module, [_readout_mux_start()]
        sets the trigger AWG and enables the capture units.

        """
        for chassis_name in c[QSConstants.ACQ_CNXT_TAG].keys():
            if chassis_name not in c[QSConstants.DAC_CNXT_TAG].keys():
                raise Exception(QSMessage.ERR_NOARMED_DAC)
            else:
                dev, awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]
                trigger_board = list(awgs)[0]

            for _dev, _module, _units in c[QSConstants.ACQ_CNXT_TAG][chassis_name]:
                _dev.set_trigger_board(trigger_board, _units)
        return

    @setting(106, "DAQ Trigger", returns=["b"])
    def daq_trigger(self, c):
        """
        Start synchronous measurement.

        Read the clock value from the master FPGA board and set a planned timing
        to the QuBE units. Measurement is to start at the given timing.

        """
        if 1 > len(c[QSConstants.DAC_CNXT_TAG].keys()):
            return False  # Nothing to start.
        delay = int(c[QSConstants.DAQ_SDLY_TAG] * QSConstants.SYNC_CLOCK + 0.5)

        chassis_list = c[QSConstants.DAC_CNXT_TAG].keys()
        tentative_master = list(chassis_list)[0]
        clock = (
            self._sync_ctrl[tentative_master].read_clock()[1] + delay
        ) & 0xFFFFFFFFFFFFFFF0
        # In a case where we use master FPGA
        # board as a trigger source
        # clock = self._master_ctrl.read_clock() + delay
        for chassis_name in chassis_list:
            skew = self.chassisSkew[chassis_name]
            dev, enabled_awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]
            awg_bitmap = 0
            for _awg in enabled_awgs:
                if 0 <= _awg and _awg < 16:
                    awg_bitmap += 1 << _awg
            resp = self._sync_ctrl[chassis_name].add_sequencer(clock + skew, awg_bitmap)
            print(chassis_name, "kick at ", clock + skew, enabled_awgs)

        return True

    @setting(107, "DAQ Stop", returns=["b"])
    def daq_stop(self, c):
        """
        Wait until synchronous measurement is done.

        """
        if 1 > len(c[QSConstants.DAC_CNXT_TAG].keys()):
            return False  # Nothing to stop

        for chassis_name in c[QSConstants.DAC_CNXT_TAG].keys():

            dev, enabled_awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]
            concurrent_deferred_obj = self._thread_pool.submit(
                dev.stop_daq, list(enabled_awgs), c[QSConstants.DAQ_TOUT_TAG]
            )
            twisted_deferred_obj = future_to_deferred(concurrent_deferred_obj)

            result = yield twisted_deferred_obj

        returnValue(True)

    @setting(112, "DAQ Clear", returns=["b"])
    def daq_clear(self, c):
        """
        Clear registed control and readout channels from the device context.

        """
        c[QSConstants.DAC_CNXT_TAG] = dict()
        c[QSConstants.ACQ_CNXT_TAG] = dict()

        return True  # Nothing to stop

    @setting(113, "DAQ Terminate", returns=["b"])
    def daq_terminate(self, c):
        """
        Force terminate a current running measurement

        """
        if 1 > len(c[QSConstants.DAC_CNXT_TAG].keys()):
            return False

        for chassis_name in c[QSConstants.DAC_CNXT_TAG].keys():
            dev, enabled_awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]
            dev.terminate_daq(list(enabled_awgs))

        for chassis_name in c[QSConstants.ACQ_CNXT_TAG].keys():
            for dev, module, units in c[QSConstants.ACQ_CNXT_TAG][chassis_name]:
                dev.terminate_acquisition(units)

        return True

    @setting(108, "DAQ Timeout", t=["v[s]"], returns=["v[s]"])
    def daq_timeout(self, c, t=None):
        if t is None:
            val = c[QSConstants.DAQ_TOUT_TAG]
            return T.Value(val, "s")
        else:
            c[QSConstants.DAQ_TOUT_TAG] = t["s"]
            return t

    @setting(111, "DAQ Synchronization Delay", t=["v[s]"], returns=["v[s]"])
    def daq_sync_delay(self, c, t=None):
        if t is None:
            val = c[QSConstants.DAQ_SDLY_TAG]
            return T.Value(val, "s")
        else:
            c[QSConstants.DAQ_SDLY_TAG] = t["s"]
            return t

    @setting(110, "DAC Channels", returns=["w"])
    def daq_channels(self, c):
        """
        Retrieve the number of available AWG channels. The number of available AWG c
        hannels is configured through adi_api_mod/v1.0.6/src/helloworld.c and the
        lane information is stored in the registry /Servers/QuBE/possible_links.

        Returns:
            channels : w
                The number of available AWG channels.
        """
        dev = self.selectedDevice(c)
        return dev.number_of_awgs

    @setting(200, "Upload Parameters", channels=["w", "*w"], returns=["b"])
    def upload_parameters(self, c, channels):
        """
        Upload channel parameters.

        Sequence setting.

        Args:
            channels : w, *w
                waveform channel   0 to 2 [The number of waveform channels - 1]
        Returns:
            success  : b
                True if successful.
        """
        dev = self.selectedDevice(c)
        channels = np.atleast_1d(channels).astype(int)
        if not dev.check_awg_channels(channels):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format(
                    "awg index", 0, dev.number_of_awgs - 1
                )
            )
        return self._register_awg_channels(c, dev, channels)

    def _register_awg_channels(self, c, dev, channels):
        """
        Register selected DAC AWG channels

        The method [_register_awg_channels()] register the enabled AWG IDs to the device
        context. This information is used in daq_start() and daq_trigger()

        Data structure:
          qube010: (dev, set{0,1,2,3,...}),
          qube011: (dev, set{0,2,15,..})
        """
        chassis_name = dev.chassis_name

        if chassis_name not in c[QSConstants.DAC_CNXT_TAG].keys():
            c[QSConstants.DAC_CNXT_TAG].update({chassis_name: (dev, set())})

        _to_be_added = list()
        for channel in channels:
            _dev, awgs = c[QSConstants.DAC_CNXT_TAG][chassis_name]

            _to_be_added = dev.get_awg_id(channel)
            awgs.add(_to_be_added)
            c[QSConstants.DAC_CNXT_TAG][chassis_name] = (_dev, awgs)

        return True

    @setting(201, "Upload Readout Parameters", muxchs=["*w", "w"], returns=["b"])
    def upload_readout_parameters(self, c, muxchs):
        """
        Upload readout demodulator parameters.

        It sends the necessary parameters for readout operation.

        Args:
            muxchs: w, *w
                multiplex channel   0 to 3 [QSConstants.ACQ_MULP-1]
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )

        muxchs = np.atleast_1d(muxchs).astype(int)
        for _mux in muxchs:
            if not dev.static_check_mux_channel_range(_mux):
                raise ValueError(
                    QSMessage.ERR_INVALID_RANG.format(
                        "muxch", 0, QSConstants.ACQ_MULP - 1
                    )
                )
        resp = dev.upload_readout_parameters(muxchs)
        if resp:
            resp = self._register_mux_channels(c, dev, muxchs)
        return resp

    def _register_mux_channels(self, c, dev, selected_mux_channels):
        """
        Register selected readout channels

        The method [_register_mux_channels()] register the selected capture module
        IDs and the selected capture units to the device context. This information
        is used in daq_start() and daq_trigger().

        """
        chassis_name = dev.chassis_name
        module_id = dev.get_capture_module_id()
        unit_ids = [dev.get_capture_unit_id(_s) for _s in selected_mux_channels]

        if chassis_name not in c[QSConstants.ACQ_CNXT_TAG].keys():
            c[QSConstants.ACQ_CNXT_TAG].update({chassis_name: list()})

        registered_ids = [
            _id for _d, _id, _u in c[QSConstants.ACQ_CNXT_TAG][chassis_name]
        ]
        try:
            addition = False
            idx = registered_ids.index(module_id)
        except ValueError as e:
            c[QSConstants.ACQ_CNXT_TAG][chassis_name].append((dev, module_id, unit_ids))
        else:
            addition = True

        if addition:
            _dev, _module_id, registered_units = c[QSConstants.ACQ_CNXT_TAG][
                chassis_name
            ][idx]
            registered_units.extend(
                [unit_id for unit_id in unit_ids if unit_id not in registered_units]
            )
            c[QSConstants.ACQ_CNXT_TAG][chassis_name][idx] = (
                dev,
                module_id,
                registered_units,
            )

        return True

    @setting(
        202,
        "Upload Waveform",
        wavedata=["*2c", "*c"],
        channels=["*w", "w"],
        returns=["b"],
    )
    def upload_waveform(self, c, wavedata, channels):
        """
        Upload waveform to FPGAs.

        Transfer 500MSa/s complex waveforms to the QuBE FPGAs.

        Args:
            wavedata : *2c,*c
                Complex waveform data with a sampling interval of 2 ns [QSConstants.
                DAC_WVSAMP_IVL]. When more than two channels, speficy the waveform
                data using list, i.e.  [data0,data1,...], or tuple (data0,data1,...)

            channels: *w, w
                List of the channels, e.g., [0,1] for the case where the number of
                rows of wavedata is more than 1. You can simply give the channel
                number to set a single-channel waveform.
        """
        dev = self.selectedDevice(c)
        channels = np.atleast_1d(channels).astype(int)
        waveforms = np.atleast_2d(wavedata).astype(complex)

        if not dev.check_awg_channels(channels):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format(
                    "awg index", 0, dev.number_of_awgs - 1
                )
            )

        resp, number_of_chans, data_length = dev.check_waveform(waveforms, channels)
        if not resp:
            raise ValueError(QSMessage.ERR_INVALID_WAVD.format(number_of_chans))

        return dev.upload_waveform(waveforms, channels)

    @setting(203, "Download Waveform", muxchs=["*w", "w"], returns=["*c", "*2c"])
    def download_waveform(self, c, muxchs):
        """
        Download acquired waveforms (or processed data points).

        Transfer waveforms or datapoints from Alevo FPGA to a host computer.

        Args:
            muxchs  : *w, w

        Returns:
            data    : *2c,*c
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )

        muxchs = np.atleast_1d(muxchs).astype(int)
        for _mux in muxchs:
            if not dev.static_check_mux_channel_range(_mux):
                raise ValueError(
                    QSMessage.ERR_INVALID_RANG.format(
                        "muxch", 0, QSConstants.ACQ_MULP - 1
                    )
                )

        data = dev.download_waveform(muxchs)

        return data

    @setting(300, "Acquisition Count", acqcount=["w"], returns=["w"])
    def acquisition_count(self, c, acqcount=None):
        """
        Read and write acquisition count.

        OBSOLETED

        Args:
           acqcount : w
                The number of acquisition in a single experiment. 1 to 8 can be set.
        """
        raise Exception('obsoleted. use "acquisition_number" instead')

    @setting(301, "Acquisition Number", muxch=["w"], acqnumb=["w"], returns=["w"])
    def acquisition_number(self, c, muxch, acqnumb=None):
        """
        Read and write the number of acquisition windows

        Setting for acquistion windows. You can have several accquisition windows in
        a single experiments.

        Args:
           muxch   : w
                Multiplex channel id. 0 to 3 [QSConstants.ACQ_MULP-1] can be set
           acqnumb : w
                The number of acquisition in a single experiment. 1 to 8 can be set.
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif acqnumb is None:
            return dev.acquisition_number_of_windows[muxch]
        elif 0 < acqnumb and acqnumb <= QSConstants.ACQ_MAXNUMCAPT:
            dev.acquisition_number_of_windows[muxch] = acqnumb
            return acqnumb
        else:
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format(
                    "Acquisition number of windows", 1, QSConstants.ACQ_MAXNUMCAPT
                )
            )

    @setting(
        302,
        "Acquisition Window",
        muxch=["w"],
        window=["*(v[s]v[s])"],
        returns=["*(v[s]v[s])"],
    )
    def acquisition_window(self, c, muxch, window=None):
        """
        Read and write acquisition windows.

        Setting for acquistion windows. You can have several accquisition windows
        in a single experiments. A windows is defined as a tuple of two timestamps
        e.g., (start, end). Multiples windows can be set like [(start1, end1),
        (start2, end2), ... ]

        Args:
            muxch: w
                multiplex channel   0 to 3 [QSConstants.ACQ_MULP-1]

            window: *(v[s]v[s])
                List of windows. The windows are given by tuples of (window start,
                window end).
        Returns:
            window: *(v[s]v[s])
                Current window setting
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif window is None:
            return [
                (T.Value(_s, "ns"), T.Value(_e, "ns"))
                for _s, _e in dev.acquisition_window[muxch]
            ]

        wl = [(int(_w[0]["ns"] + 0.5), int(_w[1]["ns"] + 0.5)) for _w in window]
        if dev.static_check_acquisition_windows(wl):
            dev.set_acquisition_window(muxch, wl)
            return window
        else:
            raise ValueError(QSMessage.ERR_INVALID_WIND)

    @setting(303, "Acquisition Mode", muxch=["w"], mode=["s"], returns=["s"])
    def acquisition_mode(self, c, muxch, mode=None):
        """
        Read and write acquisition mode

        Five (or six) acquisition modes are defined, i.e., 1, 2, 3, A, B, (C) for
        predefined experiments.

        SIGNAL PROCESSING MAP <MODE NUMBER IN THE FOLLOWING TABLES>

          DECIMATION = NO
                              |       Averaging       |
                              |    NO     |   YES     |
                ------+-------+-----------+-----------+--
                 SUM |   NO   |           |     1     |
                 MAT +--------+-----------|-----------+--
                 ION |  YES   |           |           |

          DECIMATION = YES
                              |       Averaging       |
                              |    NO     |   YES     |
                ------+-------+-----------+-----------+--
                 SUM |   NO   |     2     |     3     |
                 MAT +--------+-----------|-----------+--
                 ION |  YES   |     A     |     B     |

          DECIMATION = YES / BINARIZE = YES
                              |       Averaging       |
                              |    NO     |   YES     |
                ------+-------+-----------+-----------+--
                 SUM |   NO   |           |           |
                 MAT +--------+-----------|-----------+--
                 ION |  YES   |     C     |           |

        DEBUG, The mode "C" has not been implemented yet.

        Args:
            muxch    : w
                multiplex channel   0 to 3 [QSConstants.ACQ_MULP-1]

            mode     : s
                Acquisition mode. one of '1', '2', '3', 'A', 'B' can be set.

        Returns:
            mode     : s
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif mode is None:
            return dev.acquisition_mode[muxch]
        elif mode in QSConstants.ACQ_MODENUMBER:
            dev.set_acquisition_mode(muxch, mode)
            return mode
        else:
            raise ValueError(
                QSMessage.ERR_INVALID_ITEM.format(
                    "Acquisition mode", ",".join(QSConstants.ACQ_MODENUMBER)
                )
            )

    @setting(304, "Acquisition Mux Enable", muxch=["w"], returns=["b", "*b"])
    def acquisition_mux_enable(self, c, muxch=None):
        """
        Obtain enabled demodulation mux channels

        Mux demodulation channels are enabled in upload_readout_parameters().

        Args:
            muxch : w
                multiplex channel   0 to 3 [QSConstants.ACQ_MULP-1].
                Read all channel if None.
        Returns:
            Enabled(True)/Disabled(False) status of the channel.
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif muxch is not None and not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        else:
            chassis_name = dev.chassis_name
            resp = chassis_name in c[QSConstants.ACQ_CNXT_TAG].keys()
            if resp:
                module_enabled = c[QSConstants.ACQ_CNXT_TAG][chassis_name]
                resp = True
                try:
                    idx = [_m for _d, _m, _u in module_enabled].index(
                        dev.get_capture_module_id()
                    )
                except ValueError as e:
                    resp = False
            if resp:
                _d, _m, unit_enabled = module_enabled[idx]
                if muxch is not None:
                    resp = dev.get_capture_unit_id(muxch) in unit_enabled
                    result = True if resp else False
                else:
                    result = [
                        (dev.get_capture_unit_id(i) in unit_enabled)
                        for i in range(QSConstants.ACQ_MULP)
                    ]
            else:
                result = (
                    [False for _i in range(QSConstants.ACQ_MULP)]
                    if muxch is None
                    else False
                )
            return result

    @setting(305, "Filter Pre Coefficients", muxch=["w"], coeffs=["*c"], returns=["b"])
    def filter_pre_coefficients(self, c, muxch, coeffs):
        """
        Set complex FIR coefficients to a mux channel. (getting obsoleted)
        """
        self.acquisition_fir_coefficients(c, muxch, coeffs)
        raise Exception(
            "Tabuchi wants to rename the API to acquisition_fir_coefficients"
        )

    @setting(
        306, "Average Window Coefficients", muxch=["w"], coeffs=["*c"], returns=["b"]
    )
    def set_window_coefficients(self, c, muxch, coeffs):
        """
        Set complex window coefficients to a mux channel. (getting obsoleted)
        """
        self.acquisition_window_coefficients(c, muxch, coeffs)
        raise Exception(
            "Tabuchi wants to rename the API to acquisition_window_coefficients"
        )

    @setting(
        307, "Acquisition FIR Coefficients", muxch=["w"], coeffs=["*c"], returns=["b"]
    )
    def acquisition_fir_coefficients(self, c, muxch, coeffs):
        """
        Set complex FIR (finite impulse response) filter coefficients to a mux channel.

        In the decimation DSP logic, a 8-tap FIR filter is applied before decimation.

        Args:
            muxch : w
                Multiplex readout mux channel. 0-3 can be set

            coeffs : *c
                Complex window coefficients. The absolute values of the coeffs has
                to be less than 1.

        Returns:
            success: b
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif not dev.static_check_acquisition_fir_coefs(coeffs):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("abs(coeffs)", 0, 1)
                + QSMessage.ERR_INVALID_RANG.format(
                    "len(coeffs)", 1, QSConstants.ACQ_MAX_FCOEF
                )
            )
        else:
            dev.set_acquisition_fir_coefficient(muxch, coeffs)
        return True

    @setting(
        308,
        "Acquisition Window Coefficients",
        muxch=["w"],
        coeffs=["*c"],
        returns=["b"],
    )
    def acquisition_window_coefficients(self, c, muxch, coeffs):
        """
        Set complex window coefficients to a mux channel.

        In the summation DSP logic, a readout signal is multipled by the window
        coefficients before sum operatation for weighted demodulation.

        Args:
            muxch  : w
                Multiplex readout mux channel. 0-3 can be set

            coeffs : *c
                Complex window coefficients. The absolute values of the coeffs has
                to be less than 1.

        Returns:
            success: b
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif not dev.static_check_acquisition_window_coefs(coeffs):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("abs(coeffs)", 0, 1)
                + QSMessage.ERR_INVALID_RANG.format(
                    "len(coeffs)", 1, QSConstants.ACQ_MAX_WCOEF
                )
            )
        else:
            dev.set_acquisition_window_coefficient(muxch, coeffs)
        return True

    @setting(400, "Frequency Local", frequency=["v[Hz]"], returns=["v[Hz]"])
    def local_frequency(self, c, frequency=None):
        """
        Read and write frequency setting from/to local oscillators.

        The waveform singnals from D/A converters is upconverted using local osci-
        llators (LMX2594).

        Args:
            frequency: v[Hz]
                The mininum frequency resolution of oscillators are 100 MHz [QSCons
                tants.DAC_LO_RESOL].

        Returns:
            frequency: v[Hz]

        """
        dev = self.selectedDevice(c)
        if frequency is None:
            resp = dev.get_lo_frequency()
            frequency = T.Value(resp, "MHz")
        elif dev.static_check_lo_frequency(frequency["MHz"]):
            dev.set_lo_frequency(frequency["MHz"])
        else:
            raise ValueError(
                QSMessage.ERR_FREQ_SETTING.format("LO", QSConstants.DAC_LO_RESOL)
            )
        return frequency

    @setting(401, "Frequency TX NCO", frequency=["v[Hz]"], returns=["v[Hz]"])
    def coarse_tx_nco_frequency(self, c, frequency=None):
        """
        Read and write frequency setting from/to coarse NCOs.

        A D/A converter have multiple waveform channels. The channels have a common
        coarse NCO for upconversion. The center center frequency can be tuned with
        the coarse NCO from -6 GHz to 6 GHz.

        Args:
            frequency: v[Hz]
                The minimum resolution of NCO frequencies is 1.46484375 MHz [QSConst
                ants.DAC_CNCO_RESOL].

        Returns:
            frequency: v[Hz]

        """
        dev = self.selectedDevice(c)
        if frequency is None:
            resp = dev.get_dac_coarse_frequency()
            frequency = T.Value(resp, "MHz")
        elif dev.static_check_dac_coarse_frequency(frequency["MHz"]):
            dev.set_dac_coarse_frequency(frequency["MHz"])
        else:
            raise ValueError(
                QSMessage.ERR_FREQ_SETTING.format(
                    "TX Corse NCO", QSConstants.DAC_CNCO_RESOL
                )
            )
        return frequency

    @setting(
        402,
        "Frequency TX Fine NCO",
        channel=["w"],
        frequency=["v[Hz]"],
        returns=["v[Hz]"],
    )
    def fine_tx_nco_frequency(self, c, channel, frequency=None):
        """
        Read and write frequency setting from/to fine NCOs.

        A D/A converter havs multiple waveform channels. Each channel center frequ-
        ency can be tuned using fine NCOs from -1.5 GHz to 1.5 GHz. Note that the
        maximum frequency difference is 1.2 GHz.

        Args:
            channel  : w
                The NCO channel index. The index number corresponds to that of wave-
                form channel index.
            frequency: v[Hz]
                The minimum resolution of NCO frequencies is 0.48828125 MHz [QSConst
                ants.DAC_FNCO_RESOL].

        Returns:
            frequency: v[Hz]

        """
        dev = self.selectedDevice(c)
        if not dev.check_awg_channels([channel]):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format(
                    "awg index", 0, dev.number_of_awgs - 1
                )
            )
        elif frequency is None:
            resp = dev.get_dac_fine_frequency(channel)
            frequency = T.Value(resp, "MHz")
        elif dev.static_check_dac_fine_frequency(frequency["MHz"]):
            dev.set_dac_fine_frequency(channel, frequency["MHz"])
        else:
            raise ValueError(
                QSMessage.ERR_FREQ_SETTING.format(
                    "TX Fine NCO", QSConstants.DAC_FNCO_RESOL
                )
                + "\n"
                + QSMessage.ERR_INVALID_RANG.format(
                    "TX Fine NCO frequency",
                    "{} MHz.".format(-QSConstants.NCO_SAMPLE_F // 2),
                    "{} MHz.".format(QSConstants.NCO_SAMPLE_F // 2),
                )
            )
        return frequency

    @setting(403, "Frequency RX NCO", frequency=["v[Hz]"], returns=["v[Hz]"])
    def coarse_rx_nco_frequency(self, c, frequency=None):
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif frequency is None:
            resp = dev.get_adc_coarse_frequency()
            frequency = T.Value(resp, "MHz")
        elif dev.static_check_adc_coarse_frequency(frequency["MHz"]):
            dev.set_adc_coarse_frequency(frequency["MHz"])
        else:
            raise ValueError(
                QSMessage.ERR_FREQ_SETTING.format(
                    "RX Corse NCO", QSConstants.ADC_CNCO_RESOL
                )
            )
        return frequency

    @setting(404, "Frequency Sideband", sideband=["s"], returns=["s"])
    def sideband_selection(self, c, sideband=None):
        """
        Read and write the frequency sideband setting to the up- and down-conversion
        mixers.

        Args:
            sideband : s
                The sideband selection string. Either 'usb' or 'lsb' (QSConstants.CN
                L_MXUSB_VAL and QSConstants.CNL_MXLSB_VAL) can be set.

        Returns:
            sideband : s
                The current sideband selection string.
        """
        dev = self.selectedDevice(c)
        if sideband is None:
            sideband = dev.get_mix_sideband()
        elif sideband not in [QSConstants.CNL_MXUSB_VAL, QSConstants.CNL_MXLSB_VAL]:
            raise Exception(
                QSMessage.ERR_INVALID_ITEM.format(
                    "The sideband string",
                    "{} or {}".format(
                        QSConstants.CNL_MXUSB_VAL, QSConstants.CNL_MXLSB_VAL
                    ),
                )
            )
        else:
            dev.set_mix_sideband(sideband)
        return sideband


class QuBE_Server_debug_otasuke(QuBE_Server):

    deviceWrappers = {
        QSConstants.CNL_READ_VAL: QuBE_ReadoutLine_debug_otasuke,
        QSConstants.CNL_CTRL_VAL: QuBE_ControlLine_debug_otasuke,
    }

    def __init__(self, *args, **kw):
        QuBE_Server.__init__(self, *args, **kw)

    def instantiateChannel(self, name, channels, awg_ctrl, cap_ctrl, lsi_ctrl, info):
        devices = super(QuBE_Server_debug_otasuke, self).instantiateChannel(
            name, channels, awg_ctrl, cap_ctrl, lsi_ctrl, info
        )
        revised = []
        for device, channel in zip(devices, channels):
            name, args, kw = device
            _kw = dict(
                gsw_ctrl=lsi_ctrl.gpio, gsw_mask=channel[QSConstants.CNL_GPIOSW_TAG]
            )
            kw.update(_kw)
            revised.append((name, args, kw))
        return revised

    @setting(
        502,
        "DEBUG AWG REG",
        addr=["w"],
        offset=["w"],
        pos=["w"],
        bits=["w"],
        data=["w"],
        returns=["w"],
    )
    def debug_awg_ctrl_reg(self, c, addr, offset, pos, bits, data=None):
        """
        Read and write to the AWG registers

        It is useful for debug but should not be used for daily operation.

        Args:

            addr  : w   0x00 for master control registers
            offset: w   0x00 [32bits] version
                        0x04 [16bits] control select
                        0x08 [4bits]  awg control. bit0 reset, bit 1 prepare,
                                                   bit2 start, bit 3 terminate
                        0x10 [16bits] busy
                        0x14 [16bits] ready
                        0x18 [16bits] done
            pos   : w   Bit location
            bits  : w   Number of bits to read/write
            data  : w   Data. Read operation is performed if None
        """
        dev = self.selectedDevice(c)
        reg = (
            dev._awg_ctrl._AwgCtrl__reg_access
        )  # DEBUG _awg_ctrl is a protected member
        if data is None:
            data = reg.read_bits(addr, offset, pos, bits)
            return data
        else:
            reg.write_bits(addr, offset, pos, bits, data)
        return 0

    @setting(
        501,
        "DEBUG CAP REG",
        addr=["w"],
        offset=["w"],
        pos=["w"],
        bits=["w"],
        data=["w"],
        returns=["w"],
    )
    def debug_cap_ctrl_reg(self, c, addr, offset, pos, bits, data=None):
        """
        Read and write to the AWG registers.

        It is useful for debug but should not be used for daily operation.

        Args:
            addr  : w    0x00 for Master control registers
            offset: w    Register index. See below
                         0x00 [32bits] version
                         0x04 [5bits ] select (mod0) bit0 no trig, bit1-4 daq id
                         0x08 [5bits ] select (mod1) bit0 no trig, bit1-4 daq id
                         0x0c [8bits]  trigger mask
                         0x10 [8bits] capmod select
                         0x1c [8bits] busy
                         0x20 [8bits] done
            pos   : w    Bit location
            bits  : w    Number of bits to read/write
            data  : w    Data. Read operation is performed if None
        """
        dev = self.selectedDevice(c)
        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        reg = (
            dev._cap_ctrl._CaptureCtrl__reg_access
        )  # DEBUG _cap_ctrl is a protected member
        if data is None:
            data = reg.read_bits(addr, offset, pos, bits)
            return data
        else:
            reg.write_bits(addr, offset, pos, bits, data)
        return 0

    @setting(
        503,
        "DEBUG Auto Acquisition FIR Coefficients",
        muxch=["w"],
        bb_frequency=["v[Hz]"],
        sigma=["v[s]"],
        returns=["b"],
    )
    def debug_auto_acquisition_fir_coefficients(
        self, c, muxch, bb_frequency, sigma=None
    ):
        """
        Automatically set finite impulse resoponse filter coefficients.

        Set gauss-envelope FIR coefficients

        Args:
             muxch        : w
                Multiplex readout mux channel. 0-3 can be set

             bb_frequency : v[Hz]
                 The base-band frequency of the readout signal. It could be
                 f(readout) - f(local oscillator) - f(coase NCO frequency) when
                 upper-sideband modu- and demodulations are used.
        Returns:
             success      : b
        """

        if sigma is None:
            sigma = 3.0  # nanosecodnds

        freq_in_mhz = bb_frequency["MHz"]  # base-band frequency before decimation.
        if (
            -QSConstants.ADCBB_SAMPLE_R / 2.0 >= freq_in_mhz
            or QSConstants.ADCBB_SAMPLE_R / 2.0 <= freq_in_mhz
        ):
            raise Exception(
                QSMessage.ERR_INVALID_RANG.format(
                    "bb_frequency",
                    -QSConstants.ADCBB_SAMPLE_R / 2.0,
                    QSConstants.ADCBB_SAMPLE_R / 2.0,
                )
            )
        n_of_band = QSConstants.ACQ_MAX_FCOEF
        band_step = QSConstants.ADCBB_SAMPLE_R / n_of_band
        band_idx = int(freq_in_mhz / band_step + 0.5 + n_of_band) - n_of_band
        band_center = band_step * band_idx

        x = (
            np.arange(QSConstants.ACQ_MAX_FCOEF) - (QSConstants.ACQ_MAX_FCOEF - 1) / 2
        )  # symmetric in center.
        gaussian = np.exp(-0.5 * x**2 / (sigma**2))  # gaussian with sigma of [sigma]
        phase_factor = (
            2
            * np.pi
            * (band_center / QSConstants.ADCBB_SAMPLE_R)
            * np.arange(QSConstants.ACQ_MAX_FCOEF)
        )
        coeffs = gaussian * np.exp(1j * phase_factor) * (1 - 1e-3)

        return self.acquisition_fir_coefficients(c, muxch, coeffs)

    @setting(
        504,
        "DEBUG Auto Acquisition Window Coefficients",
        muxch=["w"],
        bb_frequency=["v[Hz]"],
        returns=["b"],
    )
    def debug_auto_acquisition_window_coefficients(self, c, muxch, bb_frequency):
        """
        Automatically set complex window coefficients

        debug_auto_acquisition_window_coefficients() sets rectangular window as a
        demodulation window. If you want to try windowed demodulation, it is better
        to give the coefs manually.

        *debug_auto_acquisition_window_coefficients() has to be called after
         acquisition_window().

        Args:
             muxch        : w
                 Multiplex readout mux channel. 0-3 can be set

             bb_frequency : v[Hz]
                 The base-band frequency of the readout signal. It could be
                 f(readout) - f(local oscillator) - f(coase NCO frequency) when
                 upper-sideband modu- and demodulations are used.
        Returns:
             success      : b
        """

        def _max_window_length(windows):
            def section_length(tuple_section):
                return tuple_section[1] - tuple_section[0]

            return max([section_length(_w) for _w in windows])

        dev = self.selectedDevice(c)
        freq_in_mhz = bb_frequency["MHz"]  # Base-band frequency before decimation

        if QSConstants.CNL_READ_VAL != dev.device_role:
            raise Exception(
                QSMessage.ERR_INVALID_DEV.format("readout", dev.device_name)
            )
        elif not dev.static_check_mux_channel_range(muxch):
            raise ValueError(
                QSMessage.ERR_INVALID_RANG.format("muxch", 0, QSConstants.ACQ_MULP - 1)
            )
        elif (
            -QSConstants.ADCBB_SAMPLE_R / 2.0 >= freq_in_mhz
            or QSConstants.ADCBB_SAMPLE_R / 2.0 <= freq_in_mhz
        ):
            raise Exception(
                QSMessage.ERR_INVALID_RANG.format(
                    "bb_frequency",
                    -QSConstants.ADCBB_SAMPLE_R / 2.0,
                    QSConstants.ADCBB_SAMPLE_R / 2.0,
                )
            )

        decim_factor = int(
            QSConstants.ADCBB_SAMPLE_R / QSConstants.ADCDCM_SAMPLE_R + 0.5
        )
        nsample = _max_window_length(dev.acquisition_window[muxch]) // (
            decim_factor * QSConstants.ADC_BBSAMP_IVL
        )
        phase_factor = (
            2 * np.pi * (freq_in_mhz / QSConstants.ADCDCM_SAMPLE_R) * np.arange(nsample)
        )
        coeffs = np.exp(-1j * phase_factor) * (1 - 1e-3)  # Rectangular window

        return self.acquisition_window_coefficients(c, muxch, coeffs)

    @setting(505, "DEBUG Microwave Switch", output=["b"], returns=["b"])
    def debug_microwave_switch(self, c, output=None):
        """
        Enable and disable a microwave switch at the output.

        Args:
            output : b (bool)
                Outputs signal if output = True. Othewise no output or loopback.
        Returns:
            output : b (bool)
                Current status of the switch.
        """
        dev = self.selectedDevice(c)
        if output is not None:
            yield dev.set_microwave_switch(output)
        else:
            output = yield dev.get_microwave_switch()
        returnValue(output)

