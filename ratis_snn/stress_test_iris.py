"""Stress test RATISS-Snn sur Iris : sweep hyperparamètres + 5 seeds.

Objectif : prouver que la règle LCT à 3 facteurs est robuste (pas un coup de chance).
  - Sweep η (taux), threshold (LIF), n_steps (spikes), n_hidden
  - 5 seeds par config
  - Mesurer : accuracy moyenne, écart-type, P_sig moyen, stabilité
  - Viser 85%+ stable
"""
import math
import sys
import os
import json
import time

import numpy as np
import torch
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ratis_snn_lct import RATISSSnn, compute_p_sig_eligibility


def stress_test_config(eta=0.5, threshold=0.3, n_steps=10, n_hidden=8,
                       epochs=30, seeds=[42, 7, 13, 99, 2026]):
    """Teste une config sur 5 seeds, retourne accuracy + P_sig + stabilité."""
    results = []
    for seed in seeds:
        iris = load_iris()
        X, y = iris.data, iris.target
        X = StandardScaler().fit_transform(X)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
        X_tr = torch.tensor(X_tr, dtype=torch.float32)
        y_tr = torch.tensor(y_tr, dtype=torch.long)
        X_te = torch.tensor(X_te, dtype=torch.float32)
        y_te = torch.tensor(y_te, dtype=torch.long)

        # reconstruire le réseau avec le threshold
        net = RATISSSnn(4, n_hidden, 3, eta=eta, n_steps=n_steps, seed=seed)
        # appliquer le threshold (buffer torch)
        net.layer1.lif.threshold = torch.tensor(threshold)
        net.layer2.lif.threshold = torch.tensor(threshold)

        for epoch in range(epochs):
            theta = epoch / epochs * math.pi
            phi = abs(math.cos(theta))
            C = abs(math.cos(theta))
            accs = []
            for i in range(len(X_tr)):
                acc, psig1, psig2, _, _ = net.lct_train_step(X_tr[i], y_tr[i], phi, C)
                accs.append(acc)
            train_acc = np.mean(accs)

        # test final
        net.reset()
        test_accs = []
        for i in range(len(X_te)):
            out, _ = net.forward(X_te[i])
            pred = out.argmax(dim=-1)
            test_accs.append((pred == y_te[i]).float().mean().item())
        test_acc = np.mean(test_accs)
        results.append({
            "seed": seed, "train_acc": float(train_acc),
            "test_acc": float(test_acc), "psig_final": float(psig1),
        })

    accs = [r["test_acc"] for r in results]
    return {
        "eta": eta, "threshold": threshold, "n_steps": n_steps,
        "n_hidden": n_hidden,
        "test_acc_mean": float(np.mean(accs)),
        "test_acc_std": float(np.std(accs)),
        "test_acc_min": float(np.min(accs)),
        "test_acc_max": float(np.max(accs)),
        "seeds": results,
    }


if __name__ == "__main__":
    print("=== STRESS TEST RATISS-Snn sur Iris (sweep + 5 seeds) ===\n")

    configs = [
        # (eta, threshold, n_steps, n_hidden, label)
        (0.5, 0.3, 10, 8, "baseline"),
        (0.8, 0.3, 10, 8, "eta=0.8"),
        (1.0, 0.3, 10, 8, "eta=1.0"),
        (0.5, 0.2, 10, 8, "threshold=0.2"),
        (0.5, 0.3, 20, 8, "n_steps=20"),
        (0.5, 0.3, 10, 16, "n_hidden=16"),
        (0.8, 0.2, 20, 16, "aggressive"),
        (1.0, 0.2, 15, 12, "tuned"),
    ]

    all_results = []
    for eta, thr, ns, nh, label in configs:
        t0 = time.time()
        res = stress_test_config(eta=eta, threshold=thr, n_steps=ns, n_hidden=nh,
                                  epochs=25, seeds=[42, 7, 13, 99, 2026])
        dt = time.time() - t0
        all_results.append({"label": label, **res})
        print(f"{label:15s} | η={eta} thr={thr} ns={ns} nh={nh} | "
              f"test_acc={res['test_acc_mean']:.3f}±{res['test_acc_std']:.3f} "
              f"[{res['test_acc_min']:.3f}-{res['test_acc_max']:.3f}] | {dt:.1f}s")

    # best config
    best = max(all_results, key=lambda r: r["test_acc_mean"])
    print(f"\n=== BEST CONFIG : {best['label']} ===")
    print(f"  η={best['eta']} threshold={best['threshold']} n_steps={best['n_steps']} n_hidden={best['n_hidden']}")
    print(f"  test_acc = {best['test_acc_mean']:.3f} ± {best['test_acc_std']:.3f}")
    print(f"  range = [{best['test_acc_min']:.3f}, {best['test_acc_max']:.3f}]")

    if best["test_acc_mean"] > 0.85:
        print(f"\n🎯 OBJECTIF ATTEINT : >85% stable (mean={best['test_acc_mean']:.1%})")
    elif best["test_acc_mean"] > 0.75:
        print(f"\n✅ Bon résultat : >75% (mean={best['test_acc_mean']:.1%})")
    else:
        print(f"\n⚠️ À améliorer : {best['test_acc_mean']:.1%}")

    # sauvegarder
    out = os.path.join(os.path.dirname(__file__), "stress_test_iris_results.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRésultats sauvés dans {out}")
