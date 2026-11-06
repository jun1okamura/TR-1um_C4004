v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 720 -470 720 -420 {lab=SENn}
N 1040 -440 1040 -400 {lab=DO}
N 640 -330 640 -310 {lab=#net1}
N 640 -250 640 -230 {lab=#net2}
N 760 -500 780 -500 {lab=LATp}
N 580 -280 600 -280 {lab=SENp}
N 680 -360 900 -360 {lab=BLp}
N 690 -500 720 -500 {lab=VDD}
N 1040 -470 1070 -470 {lab=VDD}
N 440 -360 470 -360 {lab=VSS}
N 640 -280 670 -280 {lab=VSS}
N 640 -470 640 -450 {lab=SENn}
N 580 -500 600 -500 {lab=SENp}
N 640 -500 670 -500 {lab=VDD}
N 540 -150 540 -130 {lab=VSS}
N 280 -180 500 -180 {lab=LATp}
N 540 -180 570 -180 {lab=VSS}
N 640 -550 640 -530 {lab=VDD}
N 720 -550 720 -530 {lab=VDD}
N 640 -330 640 -310 {lab=#net1}
N 440 -250 440 -230 {lab=#net2}
N 480 -280 500 -280 {lab=SENn}
N 180 -360 400 -360 {lab=BLn}
N 360 -500 390 -500 {lab=VDD}
N 610 -360 640 -360 {lab=VSS}
N 410 -280 440 -280 {lab=VSS}
N 440 -470 440 -450 {lab=SENp}
N 480 -500 500 -500 {lab=SENn}
N 410 -500 440 -500 {lab=VDD}
N 1040 -340 1040 -140 {lab=VSS}
N 980 -370 1000 -370 {lab=SENn}
N 1040 -370 1070 -370 {lab=VSS}
N 440 -550 440 -530 {lab=VDD}
N 360 -550 440 -550 {lab=VDD}
N 440 -550 640 -550 {lab=VDD}
N 540 -140 1040 -140 {lab=VSS}
N 440 -330 440 -310 {lab=#net3}
N 440 -450 440 -380 {lab=SENp}
N 640 -450 640 -390 {lab=SENn}
N 500 -500 580 -420 {lab=SENn}
N 580 -420 640 -420 {lab=SENn}
N 500 -280 580 -420 {lab=SENn}
N 500 -420 580 -500 {lab=SENp}
N 440 -420 500 -420 {lab=SENp}
N 500 -420 580 -280 {lab=SENp}
N 440 -230 640 -230 {lab=#net2}
N 540 -230 540 -210 {lab=#net2}
N 640 -420 980 -420 {lab=SENn}
N 640 -550 720 -550 {lab=VDD}
N 360 -550 360 -530 {lab=VDD}
N 100 -420 440 -420 {lab=SENp}
N 980 -470 1000 -470 {lab=SENn}
N 720 -550 1040 -550 {lab=VDD}
N 1040 -550 1040 -500 {lab=VDD}
N 1040 -420 1100 -420 {lab=DO}
N 980 -470 980 -370 {lab=SENn}
N 360 -470 360 -420 {lab=SENp}
N 40 -440 40 -400 {lab=#net4}
N 10 -470 40 -470 {lab=VDD}
N 40 -340 40 -140 {lab=VSS}
N 80 -370 100 -370 {lab=SENp}
N 10 -370 40 -370 {lab=VSS}
N 80 -470 100 -470 {lab=SENp}
N 40 -550 40 -500 {lab=VDD}
N 100 -470 100 -370 {lab=SENp}
N 40 -550 360 -550 {lab=VDD}
N 40 -140 540 -140 {lab=VSS}
N 160 -500 180 -500 {lab=PRn}
N 220 -500 250 -500 {lab=VDD}
N 220 -550 220 -530 {lab=VDD}
N 220 -470 220 -360 {lab=BLn}
N 860 -470 860 -360 {lab=BLp}
N 900 -500 920 -500 {lab=PRn}
N 830 -500 860 -500 {lab=VDD}
N 860 -550 860 -530 {lab=VDD}
N 300 -500 320 -500 {lab=LATp}
N 300 -500 300 -180 {lab=LATp}
N 980 -280 1010 -280 {lab=VSS}
N 640 -230 980 -230 {lab=#net2}
N 980 -250 980 -230 {lab=#net2}
N 980 -370 980 -310 {lab=SENn}
N 70 -280 100 -280 {lab=VSS}
N 100 -250 100 -230 {lab=#net2}
N 100 -370 100 -310 {lab=SENp}
N 100 -230 440 -230 {lab=#net2}
N 140 -280 160 -280 {lab=SENn}
N 910 -280 940 -280 {lab=SENp}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MN.sym} 400 -360 0 0 {name=XM1
model=NMOS
w=5.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MN.sym} 600 -280 0 0 {name=XM2
model=NMOS
w=5.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MP.sym} 760 -500 0 1 {name=XM3
model=PMOS
w=6.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MP.sym} 1000 -470 0 0 {name=XM4
model=PMOS
w=10.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/iopin.sym} 900 -360 0 0 {name=p1 lab=BLp}
C {devices/lab_wire.sym} 710 -500 0 0 {name=p2 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1050 -470 0 1 {name=p3 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 450 -360 0 1 {name=p4 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 650 -280 0 1 {name=p5 sig_type=std_logic lab=VSS}
C {MP.sym} 600 -500 0 0 {name=XM5
model=PMOS
w=3.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 650 -500 0 1 {name=p6 sig_type=std_logic lab=VDD}
C {MN.sym} 500 -180 0 0 {name=XM6
model=NMOS
w=10.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 550 -180 0 1 {name=p7 sig_type=std_logic lab=VSS}
C {MN.sym} 680 -360 0 1 {name=XM7
model=NMOS
w=5.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MN.sym} 480 -280 0 1 {name=XM8
model=NMOS
w=5.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MP.sym} 320 -500 0 0 {name=XM9
model=PMOS
w=6.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/iopin.sym} 180 -360 0 1 {name=p8 lab=BLn}
C {devices/lab_wire.sym} 370 -500 0 1 {name=p9 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 630 -360 0 0 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 430 -280 0 0 {name=p12 sig_type=std_logic lab=VSS}
C {MP.sym} 480 -500 0 1 {name=XM11
model=PMOS
w=3.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 430 -500 0 0 {name=p13 sig_type=std_logic lab=VDD}
C {MN.sym} 1000 -370 0 0 {name=XM12
model=NMOS
w=6.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 1050 -370 0 1 {name=p14 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 280 -180 2 1 {name=p15 lab=LATp}
C {devices/iopin.sym} 540 -550 1 1 {name=p18 lab=VDD}
C {devices/iopin.sym} 540 -130 3 1 {name=p19 lab=VSS}
C {devices/iopin.sym} 1100 -420 0 0 {name=p20 lab=DO}
C {MP.sym} 80 -470 0 1 {name=XM10
model=PMOS
w=10.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 30 -470 0 0 {name=p17 sig_type=std_logic lab=VDD}
C {MN.sym} 80 -370 0 1 {name=XM13
model=NMOS
w=6.8u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 30 -370 0 0 {name=p24 sig_type=std_logic lab=VSS}
C {MP.sym} 180 -500 0 0 {name=XM14
model=PMOS
w=3.4u
l=1.6u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 230 -500 0 1 {name=p21 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 170 -500 0 0 {name=p22 sig_type=std_logic lab=PRn}
C {MP.sym} 900 -500 0 1 {name=XM15
model=PMOS
w=3.4u
l=1.6u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 850 -500 0 0 {name=p23 sig_type=std_logic lab=VDD}
C {devices/ipin.sym} 920 -500 2 0 {name=p25 lab=PRn}
C {devices/lab_wire.sym} 770 -500 0 1 {name=p10 sig_type=std_logic lab=LATp}
C {devices/lab_wire.sym} 920 -280 0 0 {name=p16 sig_type=std_logic lab=SENp}
C {devices/lab_wire.sym} 660 -420 0 1 {name=p26 sig_type=std_logic lab=SENn}
C {MN.sym} 940 -280 0 0 {name=XM16
model=NMOS
w=3.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 990 -280 0 1 {name=p27 sig_type=std_logic lab=VSS}
C {MN.sym} 140 -280 0 1 {name=XM17
model=NMOS
w=3.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/lab_wire.sym} 90 -280 0 0 {name=p28 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 150 -280 0 1 {name=p29 sig_type=std_logic lab=SENn}
C {devices/lab_wire.sym} 380 -420 0 1 {name=p30 sig_type=std_logic lab=SENp}
