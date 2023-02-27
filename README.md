# Phased Array Microphone Gateware
![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)

Forked from the [Litex Colorlight demo](https://github.com/enjoy-digital/colorlite).

For more detail on the project see links below:

- [Blogpost](https://benwang.dev/2023/02/26/Phased-Array-Microphone.html)
- [Host software](https://github.com/kingoflolz/mic_host)
- [PCB layout and schematics, mechanical components](https://github.com/kingoflolz/mic_hardware)

## Code structure
- Board abstraction: `hw.py`
- PDM and packet FIFO: `pdm_udp.py`
- Full device: `mic_hub.py`

## Building
`python3 mic_hub.py --build --flash`