v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 720 -470 720 -450 {lab=#net1}
N 720 -390 720 -350 {lab=BLn}
N 720 -290 720 -270 {lab=#net2}
N 720 -210 720 -190 {lab=VSS}
N 640 -420 680 -420 {lab=WRn}
N 640 -320 680 -320 {lab=WRp}
N 660 -500 680 -500 {lab=Dp}
N 660 -240 680 -240 {lab=Dp}
N 660 -500 660 -240 {lab=Dp}
N 720 -370 800 -370 {lab=BLn}
N 720 -500 750 -500 {lab=VDD}
N 720 -420 750 -420 {lab=VDD}
N 720 -320 750 -320 {lab=VSS}
N 720 -240 750 -240 {lab=VSS}
N 580 -470 580 -450 {lab=Dp}
N 520 -500 540 -500 {lab=Dn}
N 580 -500 610 -500 {lab=VDD}
N 580 -210 580 -190 {lab=VSS}
N 520 -240 540 -240 {lab=Dn}
N 580 -240 610 -240 {lab=VSS}
N 580 -450 580 -270 {lab=Dp}
N 580 -370 660 -370 {lab=Dp}
N 580 -550 580 -530 {lab=VDD}
N 580 -550 720 -550 {lab=VDD}
N 720 -550 720 -530 {lab=VDD}
N 580 -190 720 -190 {lab=VSS}
N 520 -500 520 -240 {lab=Dn}
N 240 -470 240 -450 {lab=#net3}
N 240 -390 240 -350 {lab=BLp}
N 240 -290 240 -270 {lab=#net4}
N 240 -210 240 -190 {lab=VSS}
N 280 -420 320 -420 {lab=WRn}
N 280 -320 320 -320 {lab=WRp}
N 280 -500 300 -500 {lab=Dn}
N 280 -240 300 -240 {lab=Dn}
N 300 -500 300 -240 {lab=Dn}
N 160 -370 240 -370 {lab=BLp}
N 210 -500 240 -500 {lab=VDD}
N 210 -420 240 -420 {lab=VDD}
N 210 -320 240 -320 {lab=VSS}
N 210 -240 240 -240 {lab=VSS}
N 380 -470 380 -450 {lab=Dn}
N 420 -500 440 -500 {lab=DIN}
N 350 -500 380 -500 {lab=VDD}
N 380 -210 380 -190 {lab=VSS}
N 420 -240 440 -240 {lab=DIN}
N 350 -240 380 -240 {lab=VSS}
N 380 -450 380 -270 {lab=Dn}
N 300 -370 380 -370 {lab=Dn}
N 380 -550 380 -530 {lab=VDD}
N 240 -550 380 -550 {lab=VDD}
N 240 -550 240 -530 {lab=VDD}
N 240 -190 380 -190 {lab=VSS}
N 440 -500 440 -240 {lab=DIN}
N 440 -240 440 -180 {lab=DIN}
N 380 -370 520 -370 {lab=Dn}
N 320 -420 640 -420 {lab=WRn}
N 320 -320 640 -320 {lab=WRp}
N 380 -550 580 -550 {lab=VDD}
N 440 -180 440 -160 {lab=DIN}
N 380 -190 580 -190 {lab=VSS}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MN.sym} 680 -320 0 0 {name=XM1
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
C {MN.sym} 680 -240 0 0 {name=XM2
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
C {MP.sym} 680 -500 0 0 {name=XM3
model=PMOS
w=9.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MP.sym} 680 -420 0 0 {name=XM4
model=PMOS
w=9.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/iopin.sym} 800 -370 0 0 {name=p1 lab=BLn}
C {devices/lab_wire.sym} 730 -500 0 1 {name=p2 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 730 -420 0 1 {name=p3 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 730 -320 0 1 {name=p4 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 730 -240 0 1 {name=p5 sig_type=std_logic lab=VSS}
C {MP.sym} 540 -500 0 0 {name=XM5
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
C {devices/lab_wire.sym} 590 -500 0 1 {name=p6 sig_type=std_logic lab=VDD}
C {MN.sym} 540 -240 0 0 {name=XM6
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
C {devices/lab_wire.sym} 590 -240 0 1 {name=p7 sig_type=std_logic lab=VSS}
C {MN.sym} 280 -320 0 1 {name=XM7
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
C {MN.sym} 280 -240 0 1 {name=XM8
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
C {MP.sym} 280 -500 0 1 {name=XM9
model=PMOS
w=9.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MP.sym} 280 -420 0 1 {name=XM10
model=PMOS
w=9.4u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {devices/iopin.sym} 160 -370 0 1 {name=p8 lab=BLp}
C {devices/lab_wire.sym} 230 -500 0 0 {name=p9 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 230 -420 0 0 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 230 -320 0 0 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 230 -240 0 0 {name=p12 sig_type=std_logic lab=VSS}
C {MP.sym} 420 -500 0 1 {name=XM11
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
C {devices/lab_wire.sym} 370 -500 0 0 {name=p13 sig_type=std_logic lab=VDD}
C {MN.sym} 420 -240 0 1 {name=XM12
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
C {devices/lab_wire.sym} 370 -240 0 0 {name=p14 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 440 -160 1 1 {name=p15 lab=DIN}
C {devices/ipin.sym} 480 -420 1 0 {name=p16 lab=WRn}
C {devices/ipin.sym} 480 -320 3 0 {name=p17 lab=WRp}
C {devices/iopin.sym} 480 -550 1 1 {name=p18 lab=VDD}
C {devices/iopin.sym} 480 -190 3 1 {name=p19 lab=VSS}
C {devices/lab_wire.sym} 630 -370 0 0 {name=p20 sig_type=std_logic lab=Dp}
C {devices/lab_wire.sym} 470 -370 0 0 {name=p21 sig_type=std_logic lab=Dn}
