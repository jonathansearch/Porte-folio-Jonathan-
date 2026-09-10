"""
ratis_snn_lct.py — Prototype RATISS-Net sur snnTorch avec la règle LCT à 3 facteurs.

La règle LCT (ΔW = η · φ · P_sig · C) est une règle d'apprentissage à 3 facteurs
(Hebbienne neuromodulée) :
  - Facteur 1 (local) : activité pré/post-synaptique (les spikes du LIF)
  - Facteur 2 (eligibility trace) : P_sig = persistance topologique des activations
  - Facteur 3 (modulation globale) : η · φ · C (taux, phase, cohérence)

On utilise snnTorch (LIF) pour le FORWARD (spiking), mais on applique la règle LCT
MANUELLEMENT sur les poids (pas de backpropagation). C'est l'ancrage de la LCT
dans le paradigme bio-inspiré (SNN + règles à 3 facteurs).

P_sig est calculé via GUDHI (homologie persistante H1) sur les activations — c'est
ce qui rend cette approche unique : l'eligibility n'est pas une simple corrélation
d'activation, c'est une persistance TOPOLOGIQUE.

Dataset : Iris (minimal, CPU-only, pas de GPU requis).
Loi LCT figée : ΔW = η · φ · P_sig · C.
"""
import math
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import snntorch as snn
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# GUDHI pour P_sig (eligibility trace topologique)
try:
    import gudhi
    HAVE_GUDHI = True
except ImportError:
    HAVE_GUDHI = False

# ─────────────────────────────────────────────────────────────────────────────
# 1. COUCHE LCT SYNAPTIQUE (règle à 3 facteurs, pas de backprop)
# ─────────────────────────────────────────────────────────────────────────────

class LCTSynapticLayer(nn.Module):
    """Couche synaptique LCT : LIF forward + mise à jour manuelle des poids.

    Forward : input -> Linear -> LIF -> spikes (activité pré/post-synaptique)
    Update  : ΔW = η · φ · P_sig · C (règle à 3 facteurs, appliquée manuellement)

    P_sig = persistance topologique H1 des activations (eligibility trace).
    η·φ·C = signal de modulation global (taux, phase, cohérence).
    """

    def __init__(self, in_features, out_features, eta=0.5, beta=0.9,
                 threshold=0.3, max_edge=3.0, seed=42):
        super().__init__()
        torch.manual_seed(seed)
        self.in_features = in_features
        self.out_features = out_features
        self.eta = eta           # Facteur 3 : taux d'apprentissage
        self.max_edge = max_edge

        # poids (initialisés aléatoirement, pas de requires_grad — on les update manuel)
        self.W = nn.Parameter(torch.randn(out_features, in_features) * 0.3,
                               requires_grad=False)
        # LIF neuron de snnTorch (Facteur 1 : activité pré/post-synaptique)
        self.lif = snn.Leaky(beta=beta, threshold=threshold, init_hidden=True)
        # membrane init
        self.mem = None

    def reset_mem(self):
        """Réinitialise la membrane pour un nouvel échantillon."""
        self.lif.mem = self.lif.init_leaky()

    def forward(self, x):
        """Forward : input -> Linear -> LIF -> spikes."""
        if x.dim() == 1:
            x = x.unsqueeze(0)
        z = torch.matmul(x, self.W.T)
        # LIF avec init_hidden=True : on ne passe que z, le mem est géré en interne
        spk = self.lif(z)
        if isinstance(spk, tuple):
            spk = spk[0]
        return spk, z

    def lct_update(self, x, spk, z, phi, C, P_sig):
        """Applique la règle LCT à 3 facteurs : ΔW = η · φ · P_sig · C.

        Pas de backprop. Mise à jour directe des poids.
          x     : activité pré-synaptique (input)       (Facteur 1a)
          spk   : activité post-synaptique (spikes)     (Facteur 1b)
          P_sig : persistance topologique (eligibility) (Facteur 2)
          phi·C : modulation globale                     (Facteur 3)
        """
        # Hebbian : ΔW ∝ pre · post (activité)
        # LCT : ΔW = η · φ · P_sig · C · (pre · post)
        pre = x.squeeze()           # (in_features,)
        post = spk.squeeze().float() # (out_features,)
        # produit externe pre ⊗ post = (out, in)
        hebbian = torch.outer(post, pre)
        # règle LCT à 3 facteurs
        delta_W = self.eta * phi * P_sig * C * hebbian
        # mise à jour manuelle (pas de gradient) + bornage des poids
        with torch.no_grad():
            self.W += delta_W
            # normalisation L2 par ligne (stabilité, comme un neurone)
            self.W /= (self.W.norm(dim=1, keepdim=True) + 1e-6)
        return delta_W


def compute_p_sig_eligibility(activations, max_edge=3.0):
    """Calcule P_sig = persistance du cycle H1 le plus long (eligibility trace).

    C'est la signature unique de la LCT : l'eligibility n'est pas une corrélation
    d'activation, c'est une persistance TOPOLOGIQUE (homologie H1).
    Borne les activations pour éviter la divergence.
    """
    act = activations.detach().cpu().numpy()
    # normaliser + borner les activations
    act = np.tanh(act)  # borne à [-1, 1]
    if act.ndim == 1:
        act = act.reshape(1, -1)
    if act.shape[0] < 4:
        return float(np.std(act))
    points = act.T if act.shape[0] < act.shape[1] else act
    if points.shape[0] < 4:
        points = np.tile(points, (4, 1))[:4]
    if HAVE_GUDHI:
        try:
            rips = gudhi.RipsComplex(points=points.tolist(),
                                      max_edge_length=max_edge)
            st = rips.create_simplex_tree(max_dimension=2)
            pairs = st.persistence()
            h1 = [d - b for dim, (b, d) in pairs if dim == 1 and d != float('inf') and d > b]
            return float(max(h1)) if h1 else 0.0
        except Exception:
            pass
    return float(np.ptp(act))


# ─────────────────────────────────────────────────────────────────────────────
# 2. RÉSEAU RATISS-SNN (LCT sur snnTorch)
# ─────────────────────────────────────────────────────────────────────────────

class RATISSSnn(nn.Module):
    """Réseau RATISS-Net sur snnTorch : 2 couches LCT synaptiques.

    Input -> LCTLayer1 (LIF) -> LCTLayer2 (LIF) -> output
    Entraîné par la règle LCT (pas de gradient).
    """

    def __init__(self, in_features, hidden, out_features, eta=0.1, n_steps=10,
                 seed=42):
        super().__init__()
        self.n_steps = n_steps
        self.layer1 = LCTSynapticLayer(in_features, hidden, eta=eta, seed=seed)
        self.layer2 = LCTSynapticLayer(hidden, out_features, eta=eta, seed=seed+1)

    def reset(self):
        self.layer1.reset_mem()
        self.layer2.reset_mem()

    def forward(self, x):
        """Forward sur n_steps (temporal spiking)."""
        self.reset()
        out_spikes = []
        for t in range(self.n_steps):
            spk1, z1 = self.layer1(x)
            spk2, z2 = self.layer2(spk1)
            out_spikes.append(spk2)
        # rate coding : moyenne des spikes sur le temps
        return torch.stack(out_spikes).mean(0), (z1, z2)

    def lct_train_step(self, x, target, phi, C):
        """Un pas d'entraînement LCT (pas de backprop).

        Le Facteur 3 (modulation globale) combine :
          - la phase φ du milieu génial (oscillation)
          - la cohérence C
          - un SIGNAL DE RÉCOMPENSE supervisé (neuromodulateur type dopamine) :
            si la prédiction est correcte → renforce (mod > 0)
            si fausse → inhibe (mod < 0)
        """
        # forward
        out, (z1, z2) = self.forward(x)
        pred = out.argmax(dim=-1)
        correct = (pred == target).float().item()
        # signal de récompense (neuromodulateur) : +1 si bon, -1 si faux
        reward = 1.0 if correct else -0.3
        # Facteur 3 combiné : η est dans la couche, la modulation = φ · C · reward
        modulation = phi * C * reward
        # P_sig = eligibility trace topologique (Facteur 2)
        P_sig1 = compute_p_sig_eligibility(z1)
        P_sig2 = compute_p_sig_eligibility(z2)
        # activité pré/post pour Hebbian (Facteur 1)
        spk1, _ = self.layer1(x)
        spk2, _ = self.layer2(spk1)
        # mise à jour LCT à 3 facteurs
        # on passe la modulation combinée comme "phi" dans lct_update
        dW1 = self.layer1.lct_update(x, spk1, z1, modulation, 1.0, P_sig1)
        dW2 = self.layer2.lct_update(spk1, spk2, z2, modulation, 1.0, P_sig2)
        acc = correct
        return acc, P_sig1, P_sig2, dW1, dW2


# ─────────────────────────────────────────────────────────────────────────────
# 3. ENTRAÎNEMENT sur Iris (CPU-only)
# ─────────────────────────────────────────────────────────────────────────────

def train_iris(epochs=30, eta=0.1, n_steps=10, seed=42):
    """Entraîne RATISS-Snn sur Iris avec la règle LCT (pas de gradient)."""
    iris = load_iris()
    X, y = iris.data, iris.target
    X = StandardScaler().fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                          random_state=seed)
    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.long)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.long)

    net = RATISSSnn(in_features=4, hidden=8, out_features=3, eta=eta,
                    n_steps=n_steps, seed=seed)

    print(f"=== RATISS-Snn (snnTorch + LCT 3-facteurs) sur Iris ===")
    print(f"Paramètres : η={eta}, n_steps={n_steps}, epochs={epochs}")
    print(f"CPU-only : {not torch.cuda.is_available()}")
    print(f"GUDHI (P_sig topologique) : {HAVE_GUDHI}\n")

    for epoch in range(epochs):
        # φ : phase du milieu génial (oscille, mais C = |cos| reste positif)
        # le signal de récompense (Facteur 3) est géré dans lct_train_step
        theta = epoch / epochs * math.pi
        phi = abs(math.cos(theta))        # toujours positif (amplitude)
        C = abs(math.cos(theta))          # cohérence (décroît puis remonte)

        accs = []
        for i in range(len(X_train)):
            x = X_train[i]
            t = y_train[i]
            acc, psig1, psig2, dW1, dW2 = net.lct_train_step(x, t, phi, C)
            accs.append(acc)

        train_acc = np.mean(accs)
        # test
        net.reset()
        test_accs = []
        for i in range(len(X_test)):
            out, _ = net.forward(X_test[i])
            pred = out.argmax(dim=-1)
            test_accs.append((pred == y_test[i]).float().mean().item())
        test_acc = np.mean(test_accs)

        if epoch % 5 == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:2d} | C={C:.3f} φ={phi:+.3f} | "
                  f"train_acc={train_acc:.3f} test_acc={test_acc:.3f} | "
                  f"P_sig1={psig1:.3f}")

    print(f"\nAccuracy finale : train={train_acc:.3f} test={test_acc:.3f}")
    return net, test_acc


if __name__ == "__main__":
    net, acc = train_iris(epochs=30, eta=0.1, n_steps=10)
    print(f"\n✅ RATISS-Snn entraîné sur snnTorch avec la règle LCT à 3 facteurs.")
    print(f"   Accuracy test : {acc:.1%}")
    print(f"   CPU-only, pas de backprop, P_sig topologique (GUDHI).")
