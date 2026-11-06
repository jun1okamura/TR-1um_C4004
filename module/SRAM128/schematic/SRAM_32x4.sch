v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 710 -480 760 -480 {lab=VDD}
N 560 -440 690 -440 {lab=WL[0:31]}
N 490 -370 540 -370 {lab=VSS}
N 260 -440 420 -440 {lab=4*(4*A2n,4*A2p)}
N 260 -440 420 -440 {lab=4*(4*A2n,4*A2p)}
N 260 -400 420 -400 {lab=16*(A0n,A0p)}
N 260 -420 420 -420 {lab=8*(2*A1n,2*A1p)}
N 260 -460 420 -460 {lab=2*(8*A3n,8*A3p)}
N 760 -360 810 -360 {lab=VSS}
N 260 -480 420 -480 {lab=16*PR0,16*PR1}
N 440 -510 490 -510 {lab=VDD}
N 830 -440 940 -440 {lab=BLp[0:3]}
N 830 -400 940 -400 {lab=BLn[0:3]}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {BIT_CELL32.sym} 760 -420 0 0 {name=xCELL[0:3]}
C {devices/ipin.sym} 160 -610 0 0 {name=p2 lab=PR0,PR1}
C {devices/iopin.sym} 160 -340 2 0 {name=p7 lab=BLn[0:3]}
C {devices/iopin.sym} 160 -360 0 1 {name=p8 lab=BLp[0:3]}
C {devices/lab_wire.sym} 720 -480 0 1 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 880 -400 0 1 {name=p13 sig_type=std_logic lab=BLn[0:3]}
C {devices/lab_wire.sym} 880 -440 0 1 {name=p14 sig_type=std_logic lab=BLp[0:3]}
C {DEC.sym} 490 -440 0 0 {name=xDEC[0:31]}
C {devices/lab_wire.sym} 620 -440 0 0 {name=p15 sig_type=std_logic lab=WL[0:31]}
C {devices/lab_wire.sym} 500 -370 0 1 {name=p17 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 160 -530 0 0 {name=p19 lab=A0n,A1n,A2n,A3n}
C {devices/lab_wire.sym} 410 -440 0 0 {name=p22 sig_type=std_logic lab=4*(4*A2n,4*A2p)}
C {devices/lab_wire.sym} 410 -400 0 0 {name=p24 sig_type=std_logic lab=16*(A0n,A0p)}
C {devices/lab_wire.sym} 410 -420 0 0 {name=p25 sig_type=std_logic lab=8*(2*A1n,2*A1p)}
C {devices/lab_wire.sym} 410 -460 0 0 {name=p30 sig_type=std_logic lab=2*(8*A3n,8*A3p)}
C {devices/ipin.sym} 160 -550 0 0 {name=p37 lab=A0p,A1p,A2p,A3p}
C {devices/lab_wire.sym} 770 -360 0 1 {name=p47 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 420 -480 0 0 {name=p52 sig_type=std_logic lab=16*PR0,16*PR1}
C {devices/lab_wire.sym} 450 -510 0 1 {name=p48 sig_type=std_logic lab=VDD}
C {devices/iopin.sym} 160 -280 2 0 {name=p12 lab=VSS}
C {devices/iopin.sym} 160 -300 0 1 {name=p16 lab=VDD}
