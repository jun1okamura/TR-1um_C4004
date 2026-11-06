v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 380 -540 380 -500 {lab=#net1}
N 520 -570 540 -570 {lab=#net1}
N 520 -570 520 -470 {lab=#net1}
N 520 -470 540 -470 {lab=#net1}
N 380 -520 520 -520 {lab=#net1}
N 380 -200 380 -180 {lab=VSS}
N 380 -180 580 -180 {lab=VSS}
N 580 -440 580 -240 {lab=VSS}
N 380 -620 380 -600 {lab=VDD}
N 580 -620 580 -600 {lab=VDD}
N 380 -620 580 -620 {lab=VDD}
N 580 -540 580 -500 {lab=WL}
N 580 -520 640 -520 {lab=WL}
N 320 -570 340 -570 {lab=PRx}
N 320 -230 340 -230 {lab=PRx}
N 280 -570 320 -570 {lab=PRx}
N 280 -410 340 -410 {lab=A2x}
N 280 -350 340 -350 {lab=A1x}
N 280 -290 340 -290 {lab=A0x}
N 580 -570 610 -570 {lab=VDD}
N 380 -570 410 -570 {lab=VDD}
N 380 -410 410 -410 {lab=VSS}
N 380 -350 410 -350 {lab=VSS}
N 380 -290 410 -290 {lab=VSS}
N 380 -230 410 -230 {lab=VSS}
N 580 -470 610 -470 {lab=VSS}
N 320 -570 320 -230 {lab=PRx}
N 280 -470 340 -470 {lab=A3x}
N 380 -470 410 -470 {lab=VSS}
N 580 -240 580 -180 {lab=VSS}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MP.sym} 540 -570 0 0 {name=XM1
model=PMOS
w=13.6u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MN.sym} 340 -410 0 0 {name=XM2
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
C {MP.sym} 340 -570 0 0 {name=XM3
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
C {MN.sym} 540 -470 0 0 {name=XM4
model=NMOS
w=13.6u
l=1u
m=1
spiceprefix=X
as=0
ad=0
ps=0
pd=0
nrd=0
nrs=0}
C {MN.sym} 340 -350 0 0 {name=XM5
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
C {MN.sym} 340 -290 0 0 {name=XM6
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
C {MN.sym} 340 -230 0 0 {name=XM7
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
C {devices/opin.sym} 640 -520 0 0 {name=p1 lab=WL}
C {devices/ipin.sym} 280 -570 0 0 {name=p2 lab=PRx}
C {devices/ipin.sym} 280 -410 0 0 {name=p3 lab=A2x}
C {devices/ipin.sym} 280 -350 0 0 {name=p4 lab=A1x
}
C {devices/ipin.sym} 280 -290 0 0 {name=p5 lab=A0x}
C {devices/lab_wire.sym} 590 -570 0 1 {name=p6 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 390 -570 0 1 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 390 -410 0 1 {name=p8 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 390 -350 0 1 {name=p9 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 390 -290 0 1 {name=p10 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 390 -230 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 590 -470 0 1 {name=p12 sig_type=std_logic lab=VSS}
C {devices/iopin.sym} 480 -620 3 0 {name=p13 lab=VDD}
C {devices/iopin.sym} 480 -180 1 0 {name=p14 lab=VSS}
C {MN.sym} 340 -470 0 0 {name=XM9
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
C {devices/ipin.sym} 280 -470 0 0 {name=p16 lab=A3x
}
C {devices/lab_wire.sym} 390 -470 0 1 {name=p18 sig_type=std_logic lab=VSS}
