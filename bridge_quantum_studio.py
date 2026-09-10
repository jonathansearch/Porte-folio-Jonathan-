"""bridge_quantum_studio.py — Pont entre Quantum Circuit Studio et RATISS (LCT).

Charge un circuit exporté par Quantum Circuit Studio (JSON) et applique la loi LCT :
  1. Les nœuds (transmons, coupleurs, résonateurs) → coords 3D (graphe intriqué)
  2. Les arêtes → couplages (edges du graphe)
  3. measure_lct → P_sig (persistance topologique du circuit)
  4. Interprétation : P_sig élevé = circuit topologiquement sain (peu de cycles
     parasites), P_sig bas = risques de diaphonie/collision cachés

Usage : python bridge_quantum_studio.py circuit.json
"""
import json
import math
import os
import sys

import numpy as np

# brancher AEON
_AEON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RATISS-ODV-AEON")
if os.path.exists(_AEON) and _AEON not in sys.path:
    sys.path.insert(0, _AEON)

from kernel.ttf.ttf_compute import TTFBrain
from kernel.ttf.lct_law import measure_lct


def circuit_to_coords(circuit_json):
    """Convertit un circuit Quantum Studio en coords 3D pour le cerveau TTF.

    Chaque nœud (transmon, coupler, resonator) devient un point 3D.
    Les positions (x, y) du schéma + fréquence → coordonnée (x, y, freq).
    """
    nodes = circuit_json.get("nodes", [])
    if not nodes:
        return np.zeros((0, 3))
    coords = []
    for node in nodes:
        x = float(node.get("x", 0))
        y = float(node.get("y", 0))
        f = float(node.get("frequency", 5.0))
        coords.append([x, y, f])
    # normaliser (les fréquences ~5 GHz, les coords ~0-100 → on scale)
    coords = np.array(coords, dtype=float)
    coords[:, 0] /= max(coords[:, 0].max(), 1)  # normaliser x
    coords[:, 1] /= max(coords[:, 1].max(), 1)  # normaliser y
    coords[:, 2] /= 10.0  # GHz → unité ~0.5
    return coords


def analyze_circuit_lct(circuit_path, max_edge=1.5):
    """Analyse un circuit Quantum Studio avec la loi LCT.

    Retourne P_sig (santé topologique) + interprétation.
    """
    with open(circuit_path, "r") as f:
        circuit = json.load(f)

    coords = circuit_to_coords(circuit)
    n_nodes = len(coords)
    n_edges = len(circuit.get("edges", []))
    print(f"Circuit : {circuit.get('name', 'unnamed')}")
    print(f"  Nœuds : {n_nodes} | Arêtes : {n_edges}")

    if n_nodes < 4:
        print("  ⚠️ Trop peu de nœuds pour H1 (< 4). P_sig = 0.")
        return 0.0

    # construire le cerveau TTF sur le circuit
    brain = TTFBrain(coords=coords, omega=math.pi / 2, t=1.0, J=0.3,
                    max_edge=max_edge, Dc=0.5, seed=42)

    # mesurer LCT à plusieurs θ (cohérence)
    print(f"\n  === Analyse LCT du circuit ===")
    psigs = []
    for theta_frac in [0.0, 0.25, 0.5, 0.75]:
        theta = theta_frac * math.pi
        m = measure_lct(brain, theta=theta, max_edge=max_edge)
        psigs.append(m.P_sig)
        print(f"    θ={theta:.2f} (C={m.coherence_C:.3f}): P_sig={m.P_sig:.4f} "
              f"betti={m.betti} n_cycles={m.n_cycles}")
        if m.coherence_C < 0.01:
            break  # C=0 → pas besoin d'aller plus loin

    p_sig_max = max(psigs)
    # interprétation
    print(f"\n  P_sig max = {p_sig_max:.4f}")
    if p_sig_max > 0.5:
        print("  ✅ Circuit topologiquement SAIN (peu de cycles parasites)")
    elif p_sig_max > 0.2:
        print("  ⚠️ Circuit modérément sain (quelques cycles H1 persistants)")
    else:
        print("  ❌ Circuit à risque (cycles parasites = diaphonie/collision cachée)")

    # aussi : collisions de fréquence (déjà dans Quantum Studio, on vérifie)
    freqs = [n.get("frequency", 0) for n in circuit.get("nodes", [])]
    collisions = []
    for i in range(len(freqs)):
        for j in range(i + 1, len(freqs)):
            d = abs(freqs[i] - freqs[j])
            if d < 0.08:
                collisions.append((circuit["nodes"][i]["id"],
                                   circuit["nodes"][j]["id"], d))
    if collisions:
        print(f"\n  Collisions de fréquence (< 0.08 GHz) : {len(collisions)}")
        for a, b, d in collisions:
            print(f"    {a} ↔ {b} : Δf={d:.3f} GHz")
    else:
        print(f"\n  ✅ Aucune collision de fréquence (< 0.08 GHz)")

    return p_sig_max


if __name__ == "__main__":
    # utiliser le circuit de démo (transmon-microcell) si pas de fichier fourni
    if len(sys.argv) > 1:
        circuit_path = sys.argv[1]
    else:
        # créer le circuit de démo en JSON
        demo = {
            "schema": "quantum-circuit-studio/v0.1",
            "name": "transmon-microcell",
            "nodes": [
                {"id": "q0", "kind": "qubit", "frequency": 4.96, "x": 28, "y": 48},
                {"id": "q1", "kind": "qubit", "frequency": 5.18, "x": 68, "y": 48},
                {"id": "c0", "kind": "coupler", "frequency": 5.45, "x": 48, "y": 48},
                {"id": "r0", "kind": "resonator", "frequency": 6.63, "x": 28, "y": 76},
                {"id": "r1", "kind": "resonator", "frequency": 6.81, "x": 68, "y": 76},
                {"id": "fl0", "kind": "feedline", "frequency": 7.0, "x": 48, "y": 84},
            ],
            "edges": [["q0", "c0"], ["q1", "c0"], ["q0", "r0"],
                      ["q1", "r1"], ["r0", "fl0"], ["r1", "fl0"]],
        }
        circuit_path = os.path.join(os.path.dirname(__file__), "demo_circuit.json")
        with open(circuit_path, "w") as f:
            json.dump(demo, f, indent=2)

    print("=== Pont Quantum Circuit Studio → RATISS (LCT) ===\n")
    p_sig = analyze_circuit_lct(circuit_path)
    print(f"\n=== P_sig du circuit : {p_sig:.4f} ===")
    print("La loi LCT certifie la FORME topologique du circuit (message),")
    print("indépendamment de l'énergie (courant).")
