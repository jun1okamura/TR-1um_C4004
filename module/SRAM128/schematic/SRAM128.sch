v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 360 -570 460 -570 {lab=PR1}
N 240 -610 290 -610 {lab=VDD}
N 290 -490 340 -490 {lab=VSS}
N 130 -570 220 -570 {lab=CE}
N 730 -660 780 -660 {lab=VDD}
N 780 -540 830 -540 {lab=VSS}
N 590 -260 680 -260 {lab=CE}
N 590 -240 680 -240 {lab=WR}
N 130 -400 220 -400 {lab=A0,A1,A2,A3,A4}
N 240 -460 290 -460 {lab=VDD}
N 290 -340 340 -340 {lab=VSS}
N 360 -410 460 -410 {lab=A0p,A1p,A2p,A3p,A4p}
N 460 -410 510 -410 {lab=A0p,A1p,A2p,A3p,A4p}
N 360 -390 460 -390 {lab=A0n,A1n,A2n,A3n,A4n}
N 460 -390 510 -390 {lab=A0n,A1n,A2n,A3n,A4n}
N 130 -530 220 -530 {lab=A4n}
N 880 -460 940 -460 {lab=BLp[0:3]}
N 880 -370 940 -370 {lab=BLn[0:3]}
N 540 -430 680 -430 {lab=PR0,PR1}
N 540 -410 680 -410 {lab=A0p,A1p,A2p,A3p}
N 540 -390 680 -390 {lab=A0n,A1n,A2n,A3n}
N 730 -500 780 -500 {lab=VDD}
N 780 -330 830 -330 {lab=VSS}
N 730 -300 780 -300 {lab=VDD}
N 780 -160 830 -160 {lab=VSS}
N 880 -270 940 -270 {lab=BLp[0:3]}
N 880 -240 940 -240 {lab=BLn[0:3]}
N 880 -220 940 -220 {lab=DO[0:3]}
N 880 -630 940 -630 {lab=BLp[0:3]}
N 880 -570 940 -570 {lab=BLn[0:3]}
N 590 -570 680 -570 {lab=WR}
N 590 -600 680 -600 {lab=CEp}
N 590 -630 680 -630 {lab=DIN[0:3]}
N 880 -190 940 -190 {lab=CEp}
N 130 -550 220 -550 {lab=A4p
}
N 360 -530 460 -530 {lab=PR0}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {devices/ipin.sym} 90 -570 0 0 {name=p2 lab=CE}
C {devices/ipin.sym} 90 -590 0 0 {name=p4 lab=DIN[0:3]}
C {devices/iopin.sym} 90 -400 2 0 {name=p7 lab=VSS}
C {devices/iopin.sym} 90 -420 0 1 {name=p8 lab=VDD}
C {devices/ipin.sym} 90 -470 0 0 {name=p18 lab=A1}
C {devices/ipin.sym} 90 -530 0 0 {name=p19 lab=A4}
C {devices/ipin.sym} 90 -450 0 0 {name=p20 lab=A0}
C {PDEC.sym} 290 -550 0 0 {name=xPDEC}
C {devices/lab_wire.sym} 450 -570 0 0 {name=p23 sig_type=std_logic lab=PR1}
C {devices/ipin.sym} 90 -490 0 0 {name=p26 lab=A2}
C {devices/ipin.sym} 90 -510 0 0 {name=p27 lab=A3}
C {devices/lab_wire.sym} 250 -610 0 1 {name=p28 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 300 -490 0 1 {name=p29 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 210 -570 0 0 {name=p34 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 740 -660 0 1 {name=p35 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 790 -540 0 1 {name=p36 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 90 -550 0 0 {name=p37 lab=WR}
C {devices/lab_wire.sym} 670 -260 0 0 {name=p39 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 670 -240 0 0 {name=p40 sig_type=std_logic lab=WR}
C {devices/opin.sym} 1040 -600 0 0 {name=p41 lab=DO[0:3]}
C {ADB.sym} 290 -400 0 0 {name=xADB[0:4]}
C {devices/lab_wire.sym} 210 -400 0 0 {name=p32 sig_type=std_logic lab=A0,A1,A2,A3,A4}
C {devices/lab_wire.sym} 250 -460 0 1 {name=p33 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 300 -340 0 1 {name=p49 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 500 -410 0 0 {name=p50 sig_type=std_logic lab=A0p,A1p,A2p,A3p,A4p}
C {devices/lab_wire.sym} 500 -390 0 0 {name=p51 sig_type=std_logic lab=A0n,A1n,A2n,A3n,A4n}
C {devices/lab_wire.sym} 210 -530 0 0 {name=p53 sig_type=std_logic lab=A4n}
C {SRAM_32x4.sym} 780 -410 0 0 {name=xSRAM}
C {devices/lab_wire.sym} 670 -430 0 0 {name=p1 sig_type=std_logic lab=PR0,PR1}
C {devices/lab_wire.sym} 670 -410 0 0 {name=p3 sig_type=std_logic lab=A0p,A1p,A2p,A3p}
C {devices/lab_wire.sym} 670 -390 0 0 {name=p9 sig_type=std_logic lab=A0n,A1n,A2n,A3n}
C {devices/lab_wire.sym} 740 -500 0 1 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 790 -330 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {SRAM_SA4.sym} 780 -230 0 0 {name=xSA4}
C {devices/lab_wire.sym} 740 -300 0 1 {name=p5 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 790 -160 0 1 {name=p6 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 890 -460 0 1 {name=p12 sig_type=std_logic lab=BLp[0:3]}
C {devices/lab_wire.sym} 890 -370 0 1 {name=p13 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 890 -270 0 1 {name=p14 sig_type=std_logic lab=BLp[0:3]}
C {devices/lab_wire.sym} 890 -240 0 1 {name=p15 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 890 -220 0 1 {name=p16 sig_type=std_logic lab=DO[0:3]}
C {SRAM_WD4.sym} 780 -600 0 0 {name=xWD4}
C {devices/lab_wire.sym} 890 -630 0 1 {name=p17 sig_type=std_logic lab=BLp[0:3]}
C {devices/lab_wire.sym} 890 -570 0 1 {name=p22 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 670 -570 0 0 {name=p25 sig_type=std_logic lab=WR}
C {devices/lab_wire.sym} 890 -190 0 1 {name=p21 sig_type=std_logic lab=CEp}
C {devices/lab_wire.sym} 670 -600 0 0 {name=p30 sig_type=std_logic lab=CEp}
C {devices/lab_wire.sym} 670 -630 0 0 {name=p31 sig_type=std_logic lab=DIN[0:3]}
C {devices/lab_wire.sym} 210 -550 0 0 {name=p24 sig_type=std_logic lab=A4p}
C {devices/lab_wire.sym} 450 -530 0 0 {name=p38 sig_type=std_logic lab=PR0}
