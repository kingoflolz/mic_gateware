#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2021 Kazumoto Kojima <kkojima@rr.iij4u.or.jp>
# SPDX-License-Identifier: BSD-2-Clause

# The Colorlight i5 PCB and IOs have been documented by @wuxx
# https://github.com/wuxx/Colorlight-FPGA-Projects

import copy

from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
from litex.build.lattice.programmer import EcpprogProgrammer

# IOs ----------------------------------------------------------------------------------------------

_io_v7_0 = [ # Documented by @smunaut
    # Clk
    ("clk25", 0, Pins("P3"), IOStandard("LVCMOS33")),

    # Led
    ("user_led_n", 0, Pins("U16"), IOStandard("LVCMOS33")),

    # Reset button
    ("cpu_reset_n", 0, Pins("K18"), IOStandard("LVCMOS33"), Misc("PULLMODE=UP")),

    # Serial
    ("serial", 0,
        Subsignal("tx", Pins("J17")),
        Subsignal("rx", Pins("H18")),
        IOStandard("LVCMOS33")
    ),

    # SPIFlash (GD25Q16CSIG)
    ("spiflash", 0,
        Subsignal("cs_n", Pins("R2")),
        # https://github.com/m-labs/nmigen-boards/pull/38
        #Subsignal("clk",  Pins("")), driven through USRMCLK
        Subsignal("mosi", Pins("W2")),
        Subsignal("miso", Pins("V2")),
        IOStandard("LVCMOS33"),
    ),

    # SDRAM SDRAM (EM638325-6H)
    ("sdram_clock", 0, Pins("B9"), IOStandard("LVCMOS33")),
    ("sdram", 0,
        Subsignal("a", Pins(
            "B13 C14 A16 A17 B16 B15 A14 A13",
            "A12 A11 B12")),
        Subsignal("dq", Pins(
            "D15 E14 E13 D12 E12 D11 C10 B17",
            "B8  A8  C7  A7  A6  B6  A5  B5",
            "D5  C5  D6  C6  E7  D7  E8  D8",
            "E9  D9  E11 C11 C12 D13 D14 C15")),
        Subsignal("we_n",  Pins("A10")),
        Subsignal("ras_n", Pins("B10")),
        Subsignal("cas_n", Pins("A9")),
        #Subsignal("cs_n", Pins("")), # gnd
        #Subsignal("cke",  Pins("")), # 3v3
        Subsignal("ba",    Pins("B11 C8")), # sdram pin BA0 and BA1
        #Subsignal("dm",   Pins("")), # gnd
        IOStandard("LVCMOS33"),
        Misc("SLEWRATE=FAST")
    ),

    # RGMII Ethernet (B50612D)
    # The order of the two PHYs is swapped with the naming of the connectors
    # on the board so to match with the configuration of their PHYA[0] pins.
    ("eth_clocks", 0,
        Subsignal("tx", Pins("G1")),
        Subsignal("rx", Pins("H2")),
        IOStandard("LVCMOS33")
    ),
    ("eth", 0,
        Subsignal("rst_n",   Pins("P4")),
        Subsignal("mdio",    Pins("P5")),
        Subsignal("mdc",     Pins("N5")),
        Subsignal("rx_ctl",  Pins("P2")),
        Subsignal("rx_data", Pins("K2 L1 N1 P1")),
        Subsignal("tx_ctl",  Pins("K1")),
        Subsignal("tx_data", Pins("G2 H1 J1 J3")),
        IOStandard("LVCMOS33")
    ),
    ("eth_clocks", 1,
        Subsignal("tx", Pins("U19")),
        Subsignal("rx", Pins("L19")),
        IOStandard("LVCMOS33")
    ),
    ("eth", 1,
        Subsignal("rst_n",   Pins("P4")),
        Subsignal("mdio",    Pins("P5")),
        Subsignal("mdc",     Pins("N5")),
        Subsignal("rx_ctl",  Pins("M20")),
        Subsignal("rx_data", Pins("P20 N19 N20 M19")),
        Subsignal("tx_ctl",  Pins("P19")),
        Subsignal("tx_data", Pins("U20 T19 T20 R20")),
        IOStandard("LVCMOS33")
    ),

    # GPDI
    ("gpdi", 0,
        Subsignal("clk_p",   Pins("J19"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        #Subsignal("clk_n",   Pins("K19"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        Subsignal("data0_p", Pins("G19"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        #Subsignal("data0_n", Pins("H20"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        Subsignal("data1_p", Pins("E20"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        #Subsignal("data1_n", Pins("F19"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        Subsignal("data2_p", Pins("C20"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
        #Subsignal("data2_n", Pins("D19"), IOStandard("LVCMOS33D"), Misc("DRIVE=4")),
    ),

    ("pdm_clk", 0, Pins("E1"), IOStandard("LVCMOS33")),
    ("pdm_data", 0, Pins(
        "B19 B20 C20 D19 "  # channel 1
        "D20 E19 E20 F19 "  # channel 2
        "F20 G19 G20 H20 "  # channel 3
        "J19 J20 K19 K20 "  # channel 4
        "U18 U17 P18 N17 "  # channel 5
        "N18 M18 L20 L18 "  # channel 6
        "R1  T1  N1  Y2 "   # channel 7
        "W1  V1  M1  N2 "   # channel 8
        "N3  T2  M3  T3 "   # channel 9
        "R3  N4  M4  L4 "   # channel 10
        "L5  P16 J16 J18 "  # channel 11
        "J17 H18 H17 G18 "  # channel 12
        "H16 F18 G16 E18 "  # channel 13
        "F17 F16 E16 E17 "  # channel 14
        "D18 D17 G5  D16 "  # channel 15
        "F5  E6  E5  F4 "   # channel 16
        "E4  F1  F3  G3 "   # channel 17
        "H3  H4  H5  J4 "   # channel 18
        "J5  K3  K4  K5 "   # channel 19
        "B2  A2  B3  F2 "   # channel 20
        "E2  D1  D2  C1 "   # channel 21
        "B1  C2  A3  E3 "   # channel 22
        "C3  B4  C4  D3 "   # channel 23
        "A18 C17 A19 B18 "  # channel 24
    ), IOStandard("LVCMOS33")),
    # ("dbg", 0, Pins("G18"), IOStandard("LVCMOS33")),
]

# ColorLight i9 V 7.2 hardware
# See https://github.com/wuxx/Colorlight-FPGA-Projects/blob/master/colorlight_i9_v7.2.md

# SPIFlash (W25Q64JVSIQ)

_io_v7_2 = copy.deepcopy(_io_v7_0)

# Change the LED pin to "L2"

for i, x in enumerate(_io_v7_2):
    if x[:2] == ("user_led_n", 0):
        _io_v7_2[i] = ("user_led_n", 0, Pins("L2"), IOStandard("LVCMOS33"))
        break

# Append the rest of the pmod interfaces

# Platform -----------------------------------------------------------------------------------------

class Platform(LatticeECP5Platform):
    default_clk_name   = "clk25"
    default_clk_period = 1e9/25e6

    def __init__(self, board="i5", revision="7.0", toolchain="trellis"):
        if board == "i5":
            assert revision in ["7.0"]
            self.revision = revision
            device     = {"7.0": "LFE5U-25F-6BG381C"}[revision]
            io         = {"7.0": _io_v7_0}[revision]
        if board == "i9":
            assert revision in ["7.2"]
            self.revision = revision
            device     = {"7.2": "LFE5U-45F-6BG381C"}[revision]
            io         = {"7.2": _io_v7_2}[revision]

        LatticeECP5Platform.__init__(self, device, io, toolchain=toolchain)

    def create_programmer(self):
        return EcpprogProgrammer()

    def do_finalize(self, fragment):
        LatticeECP5Platform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk25",            loose=True), 1e9/25e6)
        self.add_period_constraint(self.lookup_request("eth_clocks:rx", 0, loose=True), 1e9/125e6)
        self.add_period_constraint(self.lookup_request("eth_clocks:rx", 1, loose=True), 1e9/125e6)
