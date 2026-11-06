v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 1020 -440 1050 -440 {lab=BLn}
N 1020 -440 1020 -270 {lab=BLn}
N 1020 -270 1050 -270 {lab=BLn}
N 1170 -440 1200 -440 {lab=BLp}
N 1170 -270 1200 -270 {lab=BLp}
N 1200 -440 1200 -270 {lab=BLp}
N 1020 -570 1050 -570 {lab=BLn}
N 1020 -570 1020 -440 {lab=BLn}
N 1200 -570 1200 -440 {lab=BLp}
N 1170 -570 1200 -570 {lab=BLp}
N 960 -610 1050 -610 {lab=DIN}
N 960 -230 1050 -230 {lab=PRn}
N 1110 -530 1160 -530 {lab=VSS}
N 1060 -480 1110 -480 {lab=VDD}
N 1060 -310 1110 -310 {lab=VDD}
N 920 -400 1050 -400 {lab=WL[0:31]}
N 850 -330 900 -330 {lab=VSS}
N 620 -400 780 -400 {lab=4*(4*A2n,4*A2p)}
N 620 -400 780 -400 {lab=4*(4*A2n,4*A2p)}
N 620 -360 780 -360 {lab=16*(A0n,A0p)}
N 620 -380 780 -380 {lab=8*(2*A1n,2*A1p)}
N 420 -550 520 -550 {lab=PR0,PR1}
N 300 -610 350 -610 {lab=VDD}
N 350 -490 400 -490 {lab=VSS}
N 620 -420 780 -420 {lab=2*(8*A3n,8*A3p)}
N 190 -570 280 -570 {lab=CE}
N 310 -280 360 -280 {lab=VDD}
N 360 -160 410 -160 {lab=VSS}
N 940 -230 960 -230 {lab=PRn}
N 510 -230 840 -230 {lab=PRn}
N 510 -200 950 -200 {lab=LATp}
N 200 -240 290 -240 {lab=CE}
N 200 -200 290 -200 {lab=WR}
N 1170 -220 1220 -220 {lab=DO}
N 300 -770 350 -770 {lab=VDD}
N 350 -650 400 -650 {lab=VSS}
N 190 -730 280 -730 {lab=CE}
N 190 -690 280 -690 {lab=WR}
N 960 -650 1050 -650 {lab=WRp}
N 960 -630 1050 -630 {lab=WRn}
N 420 -720 510 -720 {lab=WRp}
N 420 -700 510 -700 {lab=WRn}
N 1060 -690 1110 -690 {lab=VDD}
N 1110 -170 1160 -170 {lab=VSS}
N 1110 -360 1160 -360 {lab=VSS}
N 950 -200 1050 -200 {lab=LATp}
N 840 -230 940 -230 {lab=PRn}
N 190 -400 280 -400 {lab=A0,A1,A2,A3,A4}
N 300 -460 350 -460 {lab=VDD}
N 350 -340 400 -340 {lab=VSS}
N 420 -410 520 -410 {lab=A0p,A1p,A2p,A3p,A4p}
N 520 -410 570 -410 {lab=A0p,A1p,A2p,A3p,A4p}
N 430 -230 510 -230 {lab=PRn}
N 430 -200 510 -200 {lab=LATp}
N 420 -390 520 -390 {lab=A0,A1,A2,A3,A4}
N 520 -390 570 -390 {lab=A0,A1,A2,A3,A4}
N 620 -440 780 -440 {lab=16*PR0,16*PR1}
N 190 -530 280 -530 {lab=A4n,A4p}
N 800 -470 850 -470 {lab=VDD}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {WDRV.sym} 1110 -590 0 0 {name=xWDRV}
C {SA.sym} 1110 -240 0 0 {name=xSA}
C {BIT_CELL.sym} 1110 -420 0 0 {name=xCELL[0:31]}
C {devices/ipin.sym} 140 -570 0 0 {name=p2 lab=CE}
C {devices/ipin.sym} 140 -590 0 0 {name=p4 lab=DIN}
C {devices/iopin.sym} 140 -400 2 0 {name=p7 lab=VSS}
C {devices/iopin.sym} 140 -420 0 1 {name=p8 lab=VDD}
C {devices/lab_wire.sym} 1120 -530 0 1 {name=p9 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 1070 -480 0 1 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1070 -310 0 1 {name=p12 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1020 -510 0 0 {name=p13 sig_type=std_logic lab=BLn}
C {devices/lab_wire.sym} 1200 -510 0 1 {name=p14 sig_type=std_logic lab=BLp}
C {DEC.sym} 850 -400 0 0 {name=xDEC[0:31]}
C {devices/lab_wire.sym} 980 -400 0 0 {name=p15 sig_type=std_logic lab=WL[0:31]}
C {devices/lab_wire.sym} 860 -330 0 1 {name=p17 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 140 -470 0 0 {name=p18 lab=A1}
C {devices/ipin.sym} 140 -530 0 0 {name=p19 lab=A4}
C {devices/ipin.sym} 140 -450 0 0 {name=p20 lab=A0}
C {devices/lab_wire.sym} 770 -400 0 0 {name=p22 sig_type=std_logic lab=4*(4*A2n,4*A2p)}
C {devices/lab_wire.sym} 770 -360 0 0 {name=p24 sig_type=std_logic lab=16*(A0n,A0p)}
C {devices/lab_wire.sym} 770 -380 0 0 {name=p25 sig_type=std_logic lab=8*(2*A1n,2*A1p)}
C {PDEC.sym} 350 -550 0 0 {name=xPDEC[0:1]}
C {devices/lab_wire.sym} 510 -550 0 0 {name=p23 sig_type=std_logic lab=PR0,PR1}
C {devices/ipin.sym} 140 -490 0 0 {name=p26 lab=A2}
C {devices/ipin.sym} 140 -510 0 0 {name=p27 lab=A3}
C {devices/lab_wire.sym} 310 -610 0 1 {name=p28 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 360 -490 0 1 {name=p29 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 770 -420 0 0 {name=p30 sig_type=std_logic lab=2*(8*A3n,8*A3p)}
C {devices/lab_wire.sym} 270 -570 0 0 {name=p34 sig_type=std_logic lab=CE}
C {SACTR.sym} 360 -220 0 0 {name=xCTL}
C {devices/lab_wire.sym} 320 -280 0 1 {name=p35 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 370 -160 0 1 {name=p36 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 460 -230 0 1 {name=p5 sig_type=std_logic lab=PRn}
C {devices/lab_wire.sym} 460 -200 0 1 {name=p6 sig_type=std_logic lab=LATp}
C {devices/ipin.sym} 140 -550 0 0 {name=p37 lab=WR}
C {devices/lab_wire.sym} 280 -240 0 0 {name=p39 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 280 -200 0 0 {name=p40 sig_type=std_logic lab=WR}
C {devices/opin.sym} 1220 -220 0 0 {name=p41 lab=DO}
C {WRCTR.sym} 350 -710 0 0 {name=x1}
C {devices/lab_wire.sym} 310 -770 0 1 {name=p21 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 360 -650 0 1 {name=p31 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 270 -730 0 0 {name=p38 sig_type=std_logic lab=CE}
C {devices/lab_wire.sym} 270 -690 0 0 {name=p42 sig_type=std_logic lab=WR}
C {devices/lab_wire.sym} 1040 -650 0 0 {name=p1 sig_type=std_logic lab=WRp}
C {devices/lab_wire.sym} 1040 -630 0 0 {name=p3 sig_type=std_logic lab=WRn}
C {devices/lab_wire.sym} 1040 -610 0 0 {name=p43 sig_type=std_logic lab=DIN}
C {devices/lab_wire.sym} 500 -720 0 0 {name=p44 sig_type=std_logic lab=WRp}
C {devices/lab_wire.sym} 500 -700 0 0 {name=p45 sig_type=std_logic lab=WRn}
C {devices/lab_wire.sym} 1070 -690 0 1 {name=p46 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1120 -170 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 1120 -360 0 1 {name=p47 sig_type=std_logic lab=VSS}
C {ADB.sym} 350 -400 0 0 {name=xADB[0:4]}
C {devices/lab_wire.sym} 270 -400 0 0 {name=p32 sig_type=std_logic lab=A0,A1,A2,A3,A4}
C {devices/lab_wire.sym} 310 -460 0 1 {name=p33 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 360 -340 0 1 {name=p49 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 560 -410 0 0 {name=p50 sig_type=std_logic lab=A0p,A1p,A2p,A3p,A4p}
C {devices/lab_wire.sym} 560 -390 0 0 {name=p51 sig_type=std_logic lab=A0n,A1n,A2n,A3n,A4n}
C {devices/lab_wire.sym} 780 -440 0 0 {name=p52 sig_type=std_logic lab=16*PR0,16*PR1}
C {devices/lab_wire.sym} 270 -530 0 0 {name=p53 sig_type=std_logic lab=A4n,A4p}
C {devices/lab_wire.sym} 810 -470 0 1 {name=p48 sig_type=std_logic lab=VDD}
