v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 370 -520 370 -490 {lab=VDD}
N 370 -520 510 -520 {lab=VDD}
N 510 -520 510 -490 {lab=VDD}
N 370 -430 370 -370 {lab=#net1}
N 510 -430 510 -370 {lab=#net2}
N 370 -310 370 -280 {lab=VSS}
N 370 -280 510 -280 {lab=VSS}
N 510 -310 510 -280 {lab=VSS}
N 410 -460 420 -460 {lab=#net2}
N 420 -460 460 -400 {lab=#net2}
N 460 -400 510 -400 {lab=#net2}
N 420 -340 460 -400 {lab=#net2}
N 410 -340 420 -340 {lab=#net2}
N 460 -460 470 -460 {lab=#net1}
N 420 -400 460 -460 {lab=#net1}
N 370 -400 420 -400 {lab=#net1}
N 420 -400 460 -340 {lab=#net1}
N 460 -340 470 -340 {lab=#net1}
N 510 -340 540 -340 {lab=VSS}
N 340 -340 370 -340 {lab=VSS}
N 510 -460 540 -460 {lab=VDD}
N 340 -460 370 -460 {lab=VDD}
N 600 -450 600 -440 {lab=WL}
N 600 -400 600 -370 {lab=VSS}
N 510 -400 570 -400 {lab=#net2}
N 280 -450 280 -440 {lab=WL}
N 280 -400 280 -370 {lab=VSS}
N 310 -400 370 -400 {lab=#net1}
N 630 -400 650 -400 {lab=BLp}
N 230 -400 250 -400 {lab=BLn}
C {devices/title.sym} 160 0 0 0 {name=l1 author="Stefan Schippers"}
C {MN.sym} 470 -340 0 0 {name=XM1
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
C {MN.sym} 410 -340 0 1 {name=XM2
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
C {MP.sym} 470 -460 0 0 {name=XM3
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
C {MP.sym} 410 -460 0 1 {name=XM4
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
C {devices/iopin.sym} 440 -520 3 0 {name=p1 lab=VDD
}
C {devices/iopin.sym} 440 -280 3 1 {name=p2 lab=VSS
}
C {devices/lab_wire.sym} 520 -340 0 1 {name=p3 sig_type=std_logic lab=VSS
}
C {devices/lab_wire.sym} 360 -340 0 0 {name=p4 sig_type=std_logic lab=VSS
}
C {devices/lab_wire.sym} 520 -460 0 1 {name=p5 sig_type=std_logic lab=VDD
}
C {devices/lab_wire.sym} 360 -460 0 0 {name=p6 sig_type=std_logic lab=VDD}
C {MN.sym} 600 -440 1 0 {name=XM5
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
C {devices/lab_wire.sym} 600 -390 1 1 {name=p7 sig_type=std_logic lab=VSS
}
C {devices/ipin.sym} 600 -450 1 0 {name=p8 lab=WL}
C {MN.sym} 280 -440 3 1 {name=XM6
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
C {devices/lab_wire.sym} 280 -390 3 0 {name=p9 sig_type=std_logic lab=VSS
}
C {devices/iopin.sym} 650 -400 0 0 {name=p11 lab=BLp
}
C {devices/iopin.sym} 230 -400 0 1 {name=p12 lab=BLn}
C {devices/lab_wire.sym} 280 -450 1 0 {name=p10 sig_type=std_logic lab=WL}
