from liteeth.common import *


class PDM(Module):
    def __init__(self, clk_pad, data):
        self.clk_pad = clk_pad
        self.source = stream.Endpoint([("data", 32)])

        count = Signal(4)
        packet_id = Signal(32)

        data_reg = Signal(96)

        # pulse the clock at 0 and 8
        self.comb += self.clk_pad.eq(count[-1])

        # read the data in after waiting a bit
        self.sync += If((count & 7) == 5, data_reg.eq(data))

        # add packet id as header
        statement = If((count & 15) == 0,
                       self.source.data.eq(packet_id),
                       self.source.valid.eq(1),
                       self.source.first.eq(1))

        # clock out data 32 bits at a time
        for i in range(3):
            statement = statement.Elif((count & 7) == (i + 1),
                                       self.source.data.eq(data_reg[i * 32:(i + 1) * 32]),
                                       self.source.valid.eq(1),
                                       self.source.first.eq(0))

        self.sync += statement.Else(self.source.valid.eq(0),
                                    self.source.first.eq(0))

        # set last
        self.sync += If((count & 15) == 11, self.source.last.eq(1)).Else(self.source.last.eq(0))

        # increment count and packet id
        self.sync += count.eq(count + 1)
        self.sync += If((count & 15) == 15, packet_id.eq(packet_id + 1))


class LiteEthPacketStream2UDPTX(Module):
    def __init__(self, ip_address, udp_port, data_width=32, fifo_depth=8192):
        self.sink   = sink   = stream.Endpoint(eth_tty_tx_description(data_width))
        self.source = source = stream.Endpoint(eth_udp_user_description(data_width))

        ip_address = convert_ip(ip_address)

        max_packet = 48
        packet_counter = Signal(max=max_packet+1)

        self.submodules.fifo = fifo = stream.SyncFIFO([("data", data_width)], fifo_depth, buffered=True)
        self.comb += sink.connect(fifo.sink)

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            If((fifo.level > 512),
                NextState("SEND"),
            )
        )
        fsm.act("SEND",
            source.valid.eq(1),
            source.last.eq((packet_counter == max_packet - 1) & fifo.source.last),
            source.src_port.eq(udp_port),
            source.dst_port.eq(udp_port),
            source.ip_address.eq(ip_address),
            source.length.eq(7 * 4 * max_packet),
            source.data.eq(fifo.source.data),
            source.last_be.eq({32:0b1000, 8:0b1}[data_width]),
            If(source.ready,
                fifo.source.ready.eq(1),
                If(fifo.source.last,
                    If(packet_counter == max_packet - 1,
                       NextState("IDLE"),
                       NextValue(packet_counter, 0)
                    ).Else(
                        NextValue(packet_counter, packet_counter + 1)
                    )
                )
            )
        )


def test_pdm():
    clk = Signal()
    data = Signal(96)

    dut = PDM(clk, data)

    d = 0
    for i in range(96 // 8):
        d = (d << 8) | (i + 1)

    def testbench():
        yield data.eq(d)
        for cycle in range(200):
            yield

    run_simulation(dut, testbench(), vcd_name="basic2.vcd")