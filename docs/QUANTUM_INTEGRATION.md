# Intégration quantique — QuTiP, scQubits, NVIDIA cuQuantum

Session : intégration des librairies quantiques pour RATISS. Statut CPU-first, GPU-optional.

## 1. Ce qui est installé et validé

| Lib | Version | Rôle |
|---|---|---|
| `qutip` | 5.3.1 | Dynamique quantique (états, mesolve, Lindblad) |
| `qutip-qip` | 0.4.2 | Module circuits de QuTiP (« cqupit » proposé par Jonathan — interprété = qutip-qip ; à corriger s'il visait `qiskit` ou `cirq`) |
| `scqubits` | 4.3.1 | Qubits supraconducteurs (transmon, fluxonium, etc.) |

Validation effectuée sur machine CPU (aucun GPU présent ici) :
- Circuit H + CNOT → état de Bell, **fidélité 1.0**
- `mesolve` avec dissipateur (`qt.sigmam()`) : OK
- Transmon `scq.Transmon(EC=0.25, EJ=10.0, ng=0.0, ncut=110)` : ω₀₁ = 4.2056 GHz

## 2. NVIDIA cuQuantum — chemin d'accélération (optionnel)

QuTiP détecte cuQuantum en deux modes :

- **State-Vector** (`cuStateVec`) : `pip install qutip-cuquantum`
  - Profite d'un GPU NVIDIA + CUDA 12+ pour accélérer les circuits `qutip_qip` et les grandes dynamiques `mesolve`
  - À installer sur les machines GPU (Colab T4 incl. gratuit, ou cluster GPU Jonathan)
- **Tensor-Network** (`cuTensorNet`) : pour les calculs de réseaux de tenseurs (larges ensembles, quasi*MPS)

⚠️ **Honnêteté de session** : la machine actuelle n'a **pas de GPU** (`NO_GPU`), donc cuQuantum n'est pas installé. Le tunnel est documenté pour les machines qui en ont.

Activation cible :
```bash
pip install qutip-cuquantum
python -c "import qutip_cuquantum; print('GPU OK')"
```

## 3. scQubits — pour l'espace hyperparamètres des Hamiltonians

scQubits permet de :
- Diagonaliser des Hamiltons de qubits supraconducteurs (transmon / fluxonium) — **vitesse élevée sur CPU**
- Scanner `ng`, `EJ/EC`, `Φ` — données pour la signature topologique P_sig
- Aliment les notions d'espace parameter-landscape de la loi LCT (figée)

Exemple CPU-validé :
```python
import scqubits as scq
tm = scq.Transmon(EC=0.25, EJ=10.0, ng=0.0, ncut=110)
evals = tm.eigenvals()   # ω01, ω12, etc.
```

## 4. Où ça se branchera avec RATISS (pistes ouvertes)

1. **Cache des signatures topologiques** (calcul P_sig/GUDHI) — le bloquant pour EmoContext complet
2. **Décodeur LCT** (glouton + beam) sur sortie SNN
3. **scQubits → QuTiP** : niveaux `eigenvals` puis temps cohérence via `mesolve` — CPU suffit, GPU accélère

## 5. Commandes utiles

```bash
pip install qutip qutip-qip scqubits
python -c "import qutip, qutip_qip, scqubits as scq; print('OK')"

# GPU (optionnel) :
pip install qutip-cuquantum
```

---
*Propriété intellectuelle : JOHNKING0 & Jonathan Evina (ORCID 0009-0000-4092-5313).*
*La loi LCT est FIGÉE. Ne la change jamais.*
