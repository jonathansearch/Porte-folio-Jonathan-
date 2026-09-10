OPENQASM 3.0;
include "stdgates.inc";

// Quantum Circuit Studio logical topology export: transmon-microcell
// This file maps a schematic graph to a logical circuit scaffold.
// It is not an EM simulation, calibration schedule, or fabrication recipe.

qubit[2] q;
bit[2] c;

// Physical-to-logical register map
// q[0] ← q0 (4.96 GHz)
// q[1] ← q1 (5.18 GHz)

// Entangling topology inferred from schematic links
// coupler c0
cz q[0], q[1];

// Readout scaffold
c[0] = measure q[0];
c[1] = measure q[1];
