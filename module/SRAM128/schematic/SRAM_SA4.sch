v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 590 -440 590 -270 {lab=BLn[0:3]}
N 590 -270 620 -270 {lab=BLn[0:3]}
N 740 -270 770 -270 {lab=BLp[0:3]}
N 770 -440 770 -270 {lab=BLp[0:3]}
N 530 -220 620 -220 {lab=PRn}
N 630 -310 680 -310 {lab=VDD}
N 360 -160 410 -160 {lab=VSS}
N 510 -220 530 -220 {lab=PRn}
N 200 -240 290 -240 {lab=CE}
N 200 -200 290 -200 {lab=WR}
N 740 -220 790 -220 {lab=DO[0:3]}
N 680 -170 730 -170 {lab=VSS}
N 520 -200 620 -200 {lab=LATp}
N 430 -220 510 -220 {lab=PRn}
N 430 -200 510 -200 {lab=LATp}
N 510 -200 520 -200 {lab=LATp}
N 310 -280 360 -280 {lab=VDD}
N 450 -300 450 -240 {lab=CEn}
N 430 -240 450 -240 {lab=CEn}
N 450 -300 460 -300 {lab=CEn}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {SA.sym} 680 -240 0 0 {name=xSA[0:3]}
C {devices/ipin.sym} 140 -570 0 0 {name=p2 lab=CE}
C {devices/iopin.sym} 140 -400 2 0 {name=p7 lab=VSS}
C {devices/iopin.sym} 140 -420 0 1 {name=p8 lab=VDD}
C {devices/lab_wire.sym} 640 -310 0 1 {name=p12 sig_type=std_logic lab=VDD}
C {SACTR.sym} 360 -220 0 0 {name=xCTL}
C {devices/lab_wire.sym} 370 -160 0 1 {name=p36 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 460 -220 0 1 {name=p5 sig_type=std_logic lab=PRn}
C {devices/lab_wire.sym} 460 -200 0 1 {name=p6 sig_type=std_logic lab=LATp}
C {devices/ipin.sym} 140 -550 0 0 {name=p37 lab=WR}
C {devices/lab_wire.sym} 280 -240 0 0 {name=p39 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 280 -200 0 0 {name=p40 sig_type=std_logic lab=WR}
C {devices/opin.sym} 790 -220 0 0 {name=p41 lab=DO[0:3]}
C {devices/lab_wire.sym} 690 -170 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 320 -280 0 1 {name=p1 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 590 -390 0 1 {name=p3 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 770 -390 0 1 {name=p9 sig_type=std_logic lab=BLp[0:3]}
C {devices/iopin.sym} 140 -480 2 0 {name=p4 lab=BLn[0:3]}
C {devices/iopin.sym} 140 -500 0 1 {name=p10 lab=BLp[0:3]}
C {devices/opin.sym} 460 -300 0 0 {name=p13 lab=CEp}
