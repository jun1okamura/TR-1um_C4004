v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 320 -370 320 -330 {lab=An}
N 460 -400 480 -400 {lab=An}
N 460 -400 460 -300 {lab=An}
N 460 -300 480 -300 {lab=An}
N 320 -350 460 -350 {lab=An}
N 320 -270 320 -250 {lab=VSS}
N 320 -250 520 -250 {lab=VSS}
N 520 -270 520 -250 {lab=VSS}
N 320 -450 320 -430 {lab=VDD}
N 520 -450 520 -430 {lab=VDD}
N 320 -460 520 -460 {lab=VDD}
N 520 -370 520 -330 {lab=Ap}
N 520 -350 580 -350 {lab=Ap}
N 260 -400 280 -400 {lab=Ax}
N 260 -300 280 -300 {lab=Ax}
N 260 -400 260 -300 {lab=Ax}
N 220 -400 260 -400 {lab=Ax}
N 520 -400 550 -400 {lab=VDD}
N 320 -400 350 -400 {lab=VDD}
N 320 -300 350 -300 {lab=VSS}
N 520 -300 550 -300 {lab=VSS}
N 460 -440 580 -440 {lab=An}
N 460 -440 460 -400 {lab=An}
N 320 -460 320 -450 {lab=VDD}
N 520 -460 520 -450 {lab=VDD}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MP.sym} 280 -400 0 0 {name=XM3
model=PMOS
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
C {MN.sym} 280 -300 0 0 {name=XM7
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
C {devices/opin.sym} 580 -350 0 0 {name=p1 lab=Ap}
C {devices/ipin.sym} 220 -400 0 0 {name=p5 lab=Ax}
C {devices/lab_wire.sym} 530 -400 0 1 {name=p6 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 330 -400 0 1 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 330 -300 0 1 {name=p11 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 530 -300 0 1 {name=p12 sig_type=std_logic lab=VSS}
C {devices/iopin.sym} 420 -460 3 0 {name=p13 lab=VDD}
C {devices/iopin.sym} 420 -250 1 0 {name=p14 lab=VSS}
C {MP.sym} 480 -400 0 0 {name=XM1
model=PMOS
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
C {MN.sym} 480 -300 0 0 {name=XM2
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
C {devices/opin.sym} 580 -440 0 0 {name=p2 lab=An}
