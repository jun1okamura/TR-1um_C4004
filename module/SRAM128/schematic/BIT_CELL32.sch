v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 410 -520 440 -520 {lab=BLn}
N 410 -520 410 -350 {lab=BLn}
N 560 -520 590 -520 {lab=BLp}
N 590 -520 590 -350 {lab=BLp}
N 450 -560 500 -560 {lab=VDD}
N 310 -480 440 -480 {lab=WL[0:31]}
N 500 -440 550 -440 {lab=VSS}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {BIT_CELL.sym} 500 -500 0 0 {name=xCELL[0:31]}
C {devices/ipin.sym} 140 -590 0 0 {name=p4 lab=WL[0:31]}
C {devices/iopin.sym} 140 -400 2 0 {name=p7 lab=VSS}
C {devices/iopin.sym} 140 -420 0 1 {name=p8 lab=VDD}
C {devices/lab_wire.sym} 460 -560 0 1 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 370 -480 0 0 {name=p15 sig_type=std_logic lab=WL[0:31]}
C {devices/lab_wire.sym} 510 -440 0 1 {name=p47 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 410 -410 0 0 {name=p1 sig_type=std_logic lab=BLn}
C {devices/lab_wire.sym} 590 -410 0 0 {name=p2 sig_type=std_logic lab=BLp}
C {devices/iopin.sym} 140 -530 2 0 {name=p3 lab=BLn}
C {devices/iopin.sym} 140 -550 0 1 {name=p5 lab=BLp}
