#!/usr/bin/env python3

#
# This file is part of Colorlite.
#
# Copyright (c) 2020-2022 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import sys

from migen import *
from migen.genlib.misc import WaitTimer
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import colorlight_i5

from litex.soc.cores.clock import *
from litex.soc.cores.spi_flash import ECP5SPIFlash
from litex.soc.cores.gpio import GPIOOut
from litex.soc.cores.led import LedChaser
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import stream

from liteeth.phy.ecp5rgmii import LiteEthPHYRGMII
from litex.build.generic_platform import *
from pdm_udp import LiteEthPacketStream2UDPTX, PDM


class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys    = ClockDomain()
        # # #

        # Clk / Rst.
        clk25 = platform.request("clk25")

        # PLL.
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(clk25, 25e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

# ColorLite ----------------------------------------------------------------------------------------

class ColorLite(SoCMini):
    def __init__(self, sys_clk_freq=int(50e6), with_etherbone=True, ip_address=None, mac_address=None):
        platform     = colorlight_i5.Platform(revision="7.0")

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq)

        self.submodules.ethphy = LiteEthPHYRGMII(
            clock_pads = self.platform.request("eth_clocks", 1),
            pads       = self.platform.request("eth", 1),
            tx_delay   = 0e-9)

        self.add_etherbone(
            phy         = self.ethphy,
            ip_address  = ip_address,
            mac_address = mac_address,
            data_width  = 32,
        )
        self.submodules.pdm = PDM(platform.request("pdm_clk"), platform.request("pdm_data"))

        host_udp_port = 5678
        host_ip = "192.168.1.1"
        from liteeth.common import convert_ip

        udp_port = self.ethcore_etherbone.udp.crossbar.get_port(host_udp_port, dw=32)

        udp_streamer = LiteEthPacketStream2UDPTX(
            ip_address=convert_ip(host_ip),
            udp_port=host_udp_port,
        )
        self.submodules += udp_streamer

        self.comb += self.pdm.source.connect(udp_streamer.sink)
        self.comb += udp_streamer.source.connect(udp_port.sink)

        latch = Signal()

        self.sync += latch.eq(latch | ~self.pdm.source.ready)

        # platform.request_all("dbg").eq(latch)

        # Led --------------------------------------------------------------------------------------
        # self.submodules.leds = LedChaser(
        #     pads         = platform.request_all("user_led_n"),
        #     sys_clk_freq = sys_clk_freq, period=1)

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Take control of your ColorLight FPGA board with LiteX/LiteEth :)")
    parser.add_argument("--build",       action="store_true",      help="Build bitstream")
    parser.add_argument("--load",        action="store_true",      help="Load bitstream")
    parser.add_argument("--flash",       action="store_true",      help="Flash bitstream")
    parser.add_argument("--ip-address",  default="192.168.1.21",   help="Ethernet IP address of the board (default: 192.168.1.20).")
    parser.add_argument("--mac-address", default="0x726b895bc2e3", help="Ethernet MAC address of the board (defaullt: 0x726b895bc2e2).")
    args = parser.parse_args()

    soc     = ColorLite(ip_address=args.ip_address, mac_address=int(args.mac_address, 0))
    builder = Builder(soc, output_dir="build", csr_csv="scripts/csr.csv")
    builder.build(build_name="colorlite", run=args.build)

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0x0, builder.get_bitstream_filename(mode="sram"))

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))


if __name__ == "__main__":
    main()
