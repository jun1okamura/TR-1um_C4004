v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 700 -420 700 -380 {lab=WRp}
N 700 -500 700 -480 {lab=VDD}
N 700 -450 730 -450 {lab=VDD}
N 700 -350 730 -350 {lab=VSS}
N 640 -450 660 -450 {lab=#net1}
N 420 -230 440 -230 {lab=WR}
N 480 -230 510 -230 {lab=VSS}
N 480 -200 480 -180 {lab=VSS}
N 480 -500 700 -500 {lab=VDD}
N 480 -500 480 -480 {lab=VDD}
N 420 -450 440 -450 {lab=#net2}
N 420 -450 420 -400 {lab=#net2}
N 480 -450 510 -450 {lab=VDD}
N 420 -240 420 -230 {lab=WR}
N 380 -400 420 -400 {lab=#net2}
N 480 -420 480 -380 {lab=#net1}
N 480 -320 480 -260 {lab=#net3}
N 580 -500 580 -480 {lab=VDD}
N 540 -450 540 -290 {lab=WR}
N 380 -290 540 -290 {lab=WR}
N 580 -420 580 -400 {lab=#net1}
N 580 -450 610 -450 {lab=VDD}
N 480 -400 580 -400 {lab=#net1}
N 580 -400 640 -400 {lab=#net1}
N 640 -450 640 -400 {lab=#net1}
N 640 -400 640 -350 {lab=#net1}
N 640 -350 660 -350 {lab=#net1}
N 700 -320 700 -180 {lab=VSS}
N 480 -180 700 -180 {lab=VSS}
N 480 -350 510 -350 {lab=VSS}
N 700 -400 760 -400 {lab=WRp}
N 820 -420 820 -380 {lab=WRn}
N 820 -500 820 -480 {lab=VDD}
N 820 -450 850 -450 {lab=VDD}
N 820 -350 850 -350 {lab=VSS}
N 760 -450 780 -450 {lab=WRp}
N 760 -450 760 -400 {lab=WRp}
N 760 -400 760 -350 {lab=WRp}
N 760 -350 780 -350 {lab=WRp}
N 820 -320 820 -180 {lab=VSS}
N 820 -400 880 -400 {lab=WRn}
N 700 -500 820 -500 {lab=VDD}
N 700 -180 820 -180 {lab=VSS}
N 760 -350 760 -280 {lab=WRp}
N 760 -280 880 -280 {lab=WRp}
N 320 -420 320 -380 {lab=#net2}
N 320 -500 320 -480 {lab=VDD}
N 320 -450 350 -450 {lab=VDD}
N 320 -350 350 -350 {lab=VSS}
N 260 -450 280 -450 {lab=#net4}
N 260 -450 260 -400 {lab=#net4}
N 260 -400 260 -350 {lab=#net4}
N 260 -350 280 -350 {lab=#net4}
N 320 -320 320 -180 {lab=VSS}
N 320 -400 380 -400 {lab=#net2}
N 200 -420 200 -380 {lab=#net4}
N 200 -500 200 -480 {lab=VDD}
N 200 -450 230 -450 {lab=VDD}
N 200 -350 230 -350 {lab=VSS}
N 140 -450 160 -450 {lab=CE}
N 140 -450 140 -400 {lab=CE}
N 140 -400 140 -350 {lab=CE}
N 140 -350 160 -350 {lab=CE}
N 200 -320 200 -180 {lab=VSS}
N 200 -500 480 -500 {lab=VDD}
N 200 -180 480 -180 {lab=VSS}
N 120 -400 140 -400 {lab=CE}
N 420 -350 440 -350 {lab=#net2}
N 420 -400 420 -350 {lab=#net2}
N 420 -290 420 -240 {lab=WR}
N 200 -400 260 -400 {lab=#net4}
C {devices/opin.sym} 880 -400 0 0 {name=p1 lab=WRn}
C {devices/ipin.sym} 120 -400 0 0 {name=p2 lab=CE}
C {devices/iopin.sym} 380 -580 0 1 {name=p13 lab=VDD}
C {devices/iopin.sym} 380 -560 2 0 {name=p14 lab=VSS}
C {MN.sym} 660 -350 0 0 {name=XM1
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
C {MP.sym} 660 -450 0 0 {name=XM4
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
C {devices/lab_wire.sym} 710 -450 0 1 {name=p25 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 710 -350 0 1 {name=p26 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 490 -230 0 1 {name=p37 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} 380 -290 0 0 {name=p30 lab=WR}
C {devices/lab_wire.sym} 490 -450 0 1 {name=p31 sig_type=std_logic lab=VDD}
C {MN.sym} 440 -350 0 0 {name=XM2
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
C {MP.sym} 440 -450 0 0 {name=XM17
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
C {MN.sym} 440 -230 0 0 {name=XM18
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
C {MP.sym} 540 -450 0 0 {name=XM19
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
C {devices/lab_wire.sym} 590 -450 0 1 {name=p3 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 490 -350 0 1 {name=p4 sig_type=std_logic lab=VSS}
C {MN.sym} 780 -350 0 0 {name=XM5
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
C {MP.sym} 780 -450 0 0 {name=XM6
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
C {devices/lab_wire.sym} 830 -450 0 1 {name=p5 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 830 -350 0 1 {name=p6 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 630 -500 0 0 {name=p7 sig_type=std_logic lab=VDD
}
C {devices/lab_wire.sym} 620 -180 0 0 {name=p8 sig_type=std_logic lab=VSS
}
C {devices/opin.sym} 880 -280 0 0 {name=p9 lab=WRp}
C {MN.sym} 280 -350 0 0 {name=XM3
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
C {MP.sym} 280 -450 0 0 {name=XM7
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
C {devices/lab_wire.sym} 330 -450 0 1 {name=p10 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 330 -350 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MN.sym} 160 -350 0 0 {name=XM8
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
C {MP.sym} 160 -450 0 0 {name=XM9
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
C {devices/lab_wire.sym} 210 -450 0 1 {name=p15 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 210 -350 0 1 {name=p16 sig_type=std_logic lab=VSS}
