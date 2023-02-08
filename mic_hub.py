#!/usr/bin/env python3

from migen import *
from litex.soc.cores.clock import *
from litex.soc.cores.led import LedChaser
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from liteeth.phy.ecp5rgmii import LiteEthPHYRGMII
from liteeth.common import convert_ip

from pdm_udp import LiteEthPacketStream2UDPTX, PDM

import hw

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys    = ClockDomain()

        # Clk / Rst.
        clk25 = platform.request("clk25")

        # PLL.
        self.submodules.pll = pll = ECP5PLL()
        pll.register_clkin(clk25, 25e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)


class MicHub(SoCMini):
    def __init__(self, ip_address, host_ip_address, port, mac_address, sys_clk_freq=int(50e6),):
        platform = hw.Platform(revision="7.0")

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

        udp_port = self.ethcore_etherbone.udp.crossbar.get_port(port, dw=32)

        udp_streamer = LiteEthPacketStream2UDPTX(
            ip_address=convert_ip(host_ip_address),
            udp_port=port,
        )
        self.submodules += udp_streamer

        self.comb += self.pdm.source.connect(udp_streamer.sink)
        self.comb += udp_streamer.source.connect(udp_port.sink)

        # latch = Signal()
        #
        # self.sync += latch.eq(latch | ~self.pdm.source.ready)
        #
        # platform.request_all("dbg").eq(latch)

        # Led --------------------------------------------------------------------------------------
        self.submodules.leds = LedChaser(
            pads         = platform.request_all("user_led_n"),
            sys_clk_freq = sys_clk_freq, period=1)

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build",       action="store_true",      help="Build bitstream")
    parser.add_argument("--load",        action="store_true",      help="Load bitstream")
    parser.add_argument("--flash",       action="store_true",      help="Flash bitstream")
    parser.add_argument("--ip",          default="192.168.1.20",   help="Ethernet IP address of the board (default: 192.168.1.20).")
    parser.add_argument("--mac-address", default="0x726b895bc2e2", help="Ethernet MAC address of the board (defaullt: 0x726b895bc2e2).")
    parser.add_argument("--port",        default="5678",           help="Port to send UDP data over (default: 5678)")
    parser.add_argument("--host-ip",     default="192.168.1.1",    help="IP to send UDP data to (default: 192.168.1.1)")

    args = parser.parse_args()

    soc     = MicHub(ip_address=args.ip,
                     host_ip_address=args.host_ip,
                     port=int(args.port),
                     mac_address=int(args.mac_address, 0))

    builder = Builder(soc, output_dir="build", csr_csv="scripts/csr.csv")
    builder.build(build_name="mic_hub", run=args.build)

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0x0, builder.get_bitstream_filename(mode="sram"))

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))


if __name__ == "__main__":
    main()
