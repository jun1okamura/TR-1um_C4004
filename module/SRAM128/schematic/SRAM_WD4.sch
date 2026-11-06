v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 650 -450 680 -450 {lab=BLn[0:3]}
N 650 -450 650 -320 {lab=BLn[0:3]}
N 830 -450 830 -320 {lab=BLp[0:3]}
N 800 -450 830 -450 {lab=BLp[0:3]}
N 590 -490 680 -490 {lab=DIN[0:3]}
N 740 -410 790 -410 {lab=VSS}
N 330 -580 380 -580 {lab=VDD}
N 380 -460 430 -460 {lab=VSS}
N 220 -540 310 -540 {lab=CE}
N 220 -500 310 -500 {lab=WR}
N 590 -530 680 -530 {lab=WRp}
N 590 -510 680 -510 {lab=WRn}
N 450 -530 540 -530 {lab=WRp}
N 450 -510 540 -510 {lab=WRn}
N 690 -570 740 -570 {lab=VDD}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {WDRV.sym} 740 -470 0 0 {name=xWDRV[0:3]}
C {devices/ipin.sym} 140 -570 0 0 {name=p2 lab=CE}
C {devices/ipin.sym} 140 -590 0 0 {name=p4 lab=DIN[0:3]}
C {devices/iopin.sym} 140 -400 2 0 {name=p7 lab=VSS}
C {devices/iopin.sym} 140 -420 0 1 {name=p8 lab=VDD}
C {devices/lab_wire.sym} 750 -410 0 1 {name=p9 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 650 -390 0 0 {name=p13 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 830 -390 0 1 {name=p14 sig_type=std_logic lab=BLp[0:3]}
C {devices/ipin.sym} 140 -550 0 0 {name=p37 lab=WR}
C {WRCTR.sym} 380 -520 0 0 {name=xWRC}
C {devices/lab_wire.sym} 340 -580 0 1 {name=p21 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 390 -460 0 1 {name=p31 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 300 -540 0 0 {name=p38 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 300 -500 0 0 {name=p42 sig_type=std_logic lab=WR}
C {devices/lab_wire.sym} 670 -530 0 0 {name=p1 sig_type=std_logic lab=WRp}
C {devices/lab_wire.sym} 670 -510 0 0 {name=p3 sig_type=std_logic lab=WRn}
C {devices/lab_wire.sym} 670 -490 0 0 {name=p43 sig_type=std_logic lab=DIN[0:3]}
C {devices/lab_wire.sym} 530 -530 0 0 {name=p44 sig_type=std_logic lab=WRp}
C {devices/lab_wire.sym} 530 -510 0 0 {name=p45 sig_type=std_logic lab=WRn}
C {devices/lab_wire.sym} 700 -570 0 1 {name=p46 sig_type=std_logic lab=VDD}
C {devices/iopin.sym} 140 -480 2 0 {name=p5 lab=BLn[0:3]}
C {devices/iopin.sym} 140 -500 0 1 {name=p6 lab=BLp[0:3]}
