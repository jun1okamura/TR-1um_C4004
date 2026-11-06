v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 560 -370 560 -330 {lab=#net1}
N 700 -400 720 -400 {lab=#net1}
N 700 -400 700 -300 {lab=#net1}
N 700 -300 720 -300 {lab=#net1}
N 560 -350 700 -350 {lab=#net1}
N 560 -210 560 -190 {lab=VSS}
N 560 -190 760 -190 {lab=VSS}
N 760 -270 760 -250 {lab=VSS}
N 560 -450 560 -430 {lab=VDD}
N 760 -450 760 -430 {lab=VDD}
N 560 -450 760 -450 {lab=VDD}
N 760 -370 760 -330 {lab=PR0}
N 760 -350 820 -350 {lab=PR0}
N 500 -400 520 -400 {lab=#net2}
N 500 -240 520 -240 {lab=#net2}
N 460 -400 500 -400 {lab=#net2}
N 760 -400 790 -400 {lab=VDD}
N 560 -400 590 -400 {lab=VDD}
N 560 -240 590 -240 {lab=VSS}
N 760 -300 790 -300 {lab=VSS}
N 460 -300 520 -300 {lab=A4n}
N 760 -250 760 -190 {lab=VSS}
N 500 -400 500 -240 {lab=#net2}
N 560 -300 590 -300 {lab=VSS}
N 360 -370 360 -270 {lab=#net2}
N 200 -450 560 -450 {lab=VDD}
N 360 -450 360 -430 {lab=VDD}
N 360 -320 420 -320 {lab=#net2}
N 420 -400 420 -320 {lab=#net2}
N 420 -400 460 -400 {lab=#net2}
N 200 -190 560 -190 {lab=VSS}
N 160 -400 160 -240 {lab=CE}
N 200 -450 200 -430 {lab=VDD}
N 200 -370 200 -270 {lab=#net3}
N 200 -210 200 -190 {lab=VSS}
N 120 -320 160 -320 {lab=CE}
N 320 -400 320 -240 {lab=#net3}
N 200 -320 320 -320 {lab=#net3}
N 360 -400 390 -400 {lab=VDD}
N 200 -400 230 -400 {lab=VDD}
N 360 -240 390 -240 {lab=VSS}
N 200 -240 230 -240 {lab=VSS}
N 360 -210 360 -190 {lab=VSS}
N 560 -740 560 -700 {lab=#net4}
N 700 -770 720 -770 {lab=#net4}
N 700 -770 700 -670 {lab=#net4}
N 700 -670 720 -670 {lab=#net4}
N 560 -720 700 -720 {lab=#net4}
N 560 -580 560 -560 {lab=VSS}
N 560 -560 760 -560 {lab=VSS}
N 760 -640 760 -620 {lab=VSS}
N 560 -820 560 -800 {lab=VDD}
N 760 -820 760 -800 {lab=VDD}
N 560 -820 760 -820 {lab=VDD}
N 760 -740 760 -700 {lab=PR1}
N 760 -720 820 -720 {lab=PR1}
N 500 -770 520 -770 {lab=#net2}
N 500 -610 520 -610 {lab=#net2}
N 760 -770 790 -770 {lab=VDD}
N 560 -770 590 -770 {lab=VDD}
N 560 -610 590 -610 {lab=VSS}
N 760 -670 790 -670 {lab=VSS}
N 460 -670 520 -670 {lab=A4p}
N 760 -620 760 -560 {lab=VSS}
N 500 -770 500 -610 {lab=#net2}
N 560 -670 590 -670 {lab=VSS}
N 420 -610 420 -400 {lab=#net2}
N 420 -610 500 -610 {lab=#net2}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MP.sym} 520 -400 0 0 {name=XM3
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
C {MN.sym} 520 -240 0 0 {name=XM7
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
C {devices/opin.sym} 820 -350 0 0 {name=p1 lab=PR0}
C {devices/ipin.sym} 120 -320 0 0 {name=p5 lab=CE}
C {devices/lab_wire.sym} 770 -400 0 1 {name=p6 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 570 -400 0 1 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 570 -240 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 770 -300 0 1 {name=p12 sig_type=std_logic lab=VSS}
C {devices/iopin.sym} 660 -450 3 0 {name=p13 lab=VDD}
C {devices/iopin.sym} 660 -190 1 0 {name=p14 lab=VSS}
C {MP.sym} 720 -400 0 0 {name=XM1
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
C {MN.sym} 720 -300 0 0 {name=XM2
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
C {MN.sym} 520 -300 0 0 {name=XM4
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
C {devices/ipin.sym} 460 -300 0 0 {name=p2 lab=A4n}
C {devices/lab_wire.sym} 570 -300 0 1 {name=p3 sig_type=std_logic lab=VSS}
C {MP.sym} 320 -400 0 0 {name=XM5
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
C {MN.sym} 320 -240 0 0 {name=XM6
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
C {MP.sym} 160 -400 0 0 {name=XM8
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
C {MN.sym} 160 -240 0 0 {name=XM9
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
C {devices/lab_wire.sym} 370 -400 0 1 {name=p4 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 210 -400 0 1 {name=p8 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 370 -240 0 1 {name=p9 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 210 -240 0 1 {name=p10 sig_type=std_logic lab=VSS}
C {MP.sym} 520 -770 0 0 {name=XM10
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
C {MN.sym} 520 -610 0 0 {name=XM11
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
C {devices/opin.sym} 820 -720 0 0 {name=p15 lab=PR1}
C {devices/lab_wire.sym} 770 -770 0 1 {name=p16 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 570 -770 0 1 {name=p17 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 570 -610 0 1 {name=p18 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 770 -670 0 1 {name=p19 sig_type=std_logic lab=VSS}
C {MP.sym} 720 -770 0 0 {name=XM12
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
C {MN.sym} 720 -670 0 0 {name=XM13
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
C {MN.sym} 520 -670 0 0 {name=XM14
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
C {devices/ipin.sym} 460 -670 0 0 {name=p22 lab=A4p}
C {devices/lab_wire.sym} 570 -670 0 1 {name=p23 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 640 -820 0 1 {name=p20 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 640 -560 0 1 {name=p21 sig_type=std_logic lab=VSS}
