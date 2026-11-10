module \$_DFFE_PN0P_ (input D, C, R, E, output Q);
  wire qb_unused;
  MUXDFFRB _TECHMAP_REPLACE_ (
    .CK(C),
    .A(Q),
    .B(D),
    .S(E),
    .RSTB(R),
    .Q(Q),
    .QB(qb_unused)
  );
endmodule

module \$_DFFE_PN0N_ (input D, C, R, E, output Q);
  wire qb_unused;
  MUXDFFRB _TECHMAP_REPLACE_ (
    .CK(C),
    .A(D),
    .B(Q),
    .S(E),
    .RSTB(R),
    .Q(Q),
    .QB(qb_unused)
  );
endmodule
