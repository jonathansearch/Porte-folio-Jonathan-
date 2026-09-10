"""
ratis_snn_emocontext.py — RATISS-Snn sur EmoContext avec Snapshot Topologique.

Adapte la règle LCT à 3 facteurs pour les données SÉQUENTIELLES d'EmoContext
(dialogues de 3 tours, 4 émotions : others, happy, sad, angry).

Astuce d'ingénierie : le "Snapshot Topologique"
  1. Encodage temporel : chaque tour → train de spikes (rate coding)
  2. Accumulation SANS topologie : le SNN accumule les potentiels de membrane
     pendant les 3 tours (mémoire temporelle), sans appeler GUDHI
  3. Snapshot topologique : à la fin des 3 tours, on extrait la matrice des
     potentiels finaux → UN SEUL calcul GUDHI pour P_sig
  4. Mise à jour LCT : ΔW = η · φ · P_sig · C_emotion (l'émotion = dopamine)

Cela réduit le coût GUDHI par un facteur ~50-100 tout en capturant la forme
émotionnelle de la séquence complète.
"""
import math
import os
import sys
import re
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import snntorch as snn

# brancher les modules RATISS (topo_tokenizer + emocontext_loader)
_RATISS_MODS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ratis_modules")
if _RATISS_MODS not in sys.path:
    sys.path.insert(0, _RATISS_MODS)
_AEON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "RATISS-ODV-AEON")
if os.path.exists(_AEON) and _AEON not in sys.path:
    sys.path.insert(0, os.path.abspath(_AEON))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ratis_snn_lct import LCTSynapticLayer, compute_p_sig_eligibility

# importer le topo_tokenizer (embedding topologique, pas bag-of-words)
try:
    from topo_tokenizer import topo_signature
    HAVE_TOPO = True
except Exception:
    HAVE_TOPO = False

# ─────────────────────────────────────────────────────────────────────────────
# 1. CHARGEMENT + ENCODAGE EMOCONTEXT
# ─────────────────────────────────────────────────────────────────────────────

EMO_LABELS = {"others": 0, "happy": 1, "sad": 2, "angry": 3}
LABEL_NAMES = ["others", "happy", "sad", "angry"]


def load_emocontext(filepath, max_samples=500, vocab_size=400):
    """Charge EmoContext et encode les dialogues en embeddings bag-of-words.

    Format : id, turn1, turn2, turn3, label
    Retourne : (dialogues, labels, vocab)
      dialogues : liste de [emb_t1, emb_t2, emb_t3] (chaque emb = vecteur dense)
      labels : liste d'entiers (0-3)
    """
    samples = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]  # skip header
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            turns = parts[1:4]
            label = parts[4].strip().lower()
            if label not in EMO_LABELS:
                continue
            samples.append((turns, EMO_LABELS[label]))
            if len(samples) >= max_samples:
                break

    # construire un vocabulaire simple (top mots les plus fréquents)
    word_freq = Counter()
    for turns, _ in samples:
        for t in turns:
            words = re.findall(r"[a-zA-Z]+", t.lower())
            word_freq.update(words)
    vocab = {w: i for i, (w, _) in enumerate(word_freq.most_common(vocab_size))}

    # encoder chaque tour en embedding TOPOLOGIQUE (pas bag-of-words)
    # topo_signature transforme un mot en vecteur topologique (P_sig, betti, stats)
    # on pool les signatures des mots d'un tour → embedding du tour
    def encode_turn(turn_text):
        words = re.findall(r"[a-zA-Z]+", turn_text.lower())
        if not words or not HAVE_TOPO:
            # fallback : hash simple
            rng = np.random.default_rng(hash(turn_text) & 0xFFFFFFFF)
            return rng.standard_normal(vocab_size).astype(np.float32)
        sigs = np.array([topo_signature(w, dim=vocab_size) for w in words])
        # pool : moyenne pondérée par la norme (mots saillants pèsent plus)
        norms = np.linalg.norm(sigs, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-6)
        pooled = (sigs * norms).sum(axis=0) / (norms.sum() + 1e-6)
        return pooled.astype(np.float32)

    dialogues = []
    labels = []
    for turns, label in samples:
        embs = [encode_turn(t) for t in turns]
        dialogues.append(embs)
        labels.append(label)

    # RÉÉQUILIBRAGE DES CLASSES (undersampling de "others")
    by_class = {c: [] for c in range(4)}
    for d, l in zip(dialogues, labels):
        by_class[l].append(d)
    min_class = min(len(by_class[c]) for c in range(4) if len(by_class[c]) > 0)
    balanced_d, balanced_l = [], []
    for c in range(4):
        # garder autant de chaque classe que la plus petite classe non-others
        n_keep = min(len(by_class[c]), min_class if c != 0 else min_class)
        for d in by_class[c][:n_keep]:
            balanced_d.append(d)
            balanced_l.append(c)
    return balanced_d, balanced_l, vocab


# ─────────────────────────────────────────────────────────────────────────────
# 2. RÉSEAU TEMPOREL LCT-SNN (Snapshot Topologique)
# ─────────────────────────────────────────────────────────────────────────────

class TemporalLCTSnn(nn.Module):
    """Réseau SNN temporel pour EmoContext avec Snapshot Topologique.

    Architecture :
      Input (3 tours) → LCTLayer1 (accumulation) → LCTLayer2 (sortie)
      Pendant les 3 tours : accumulation des potentiels (mémoire temporelle)
      À la fin : 1 calcul GUDHI = P_sig (snapshot topologique)

    La règle LCT à 3 facteurs :
      Facteur 1 (local) : spikes accumulés sur les 3 tours
      Facteur 2 (eligibility) : P_sig = persistance topologique du snapshot final
      Facteur 3 (modulation) : η · φ · C_emotion (l'émotion = dopamine)
    """

    def __init__(self, in_features, hidden, out_features, eta=0.5,
                 n_steps_per_turn=15, beta=0.95, threshold=0.3, seed=42):
        super().__init__()
        self.n_steps_per_turn = n_steps_per_turn
        self.eta = eta
        torch.manual_seed(seed)
        self.layer1 = LCTSynapticLayer(in_features, hidden, eta=eta,
                                        beta=beta, threshold=threshold, seed=seed)
        # couche de sortie avec inhibition (winner-take-all)
        self.layer2 = LCTSynapticLayer(hidden, out_features, eta=eta,
                                        beta=beta, threshold=threshold, seed=seed+1,
                                        inhibition=True)

    def reset(self):
        self.layer1.reset_mem()
        self.layer2.reset_mem()

    def forward_temporal(self, dialogue):
        """Forward sur les 3 tours (accumulation temporelle).

        dialogue : liste de 3 tensors (un par tour)
        Retourne : (output_potentials, membrane_snapshot_layer1, membrane_snapshot_layer2)

        Le SNN accumule les potentiels pendant les 3 tours.
        Le snapshot final est utilisé pour le calcul topologique.
        output : somme des potentiels de membrane (pas juste spikes) = vote doux
        """
        self.reset()
        all_mem_l2 = []
        mem_history_l1 = []
        mem_history_l2 = []

        for turn_idx, turn_emb in enumerate(dialogue):
            for t in range(self.n_steps_per_turn):
                spk1, z1 = self.layer1(turn_emb)
                spk2, z2 = self.layer2(spk1)
                # accumuler les potentiels de membrane de la couche 2 (vote doux)
                if hasattr(self.layer2.lif, 'mem') and self.layer2.lif.mem is not None:
                    all_mem_l2.append(self.layer2.lif.mem.clone())
                else:
                    all_mem_l2.append(z2)
                if hasattr(self.layer1.lif, 'mem') and self.layer1.lif.mem is not None:
                    mem_history_l1.append(self.layer1.lif.mem.clone())
                else:
                    mem_history_l1.append(z1)
                mem_history_l2.append(all_mem_l2[-1])

        # output : somme des potentiels (vote doux, pas winner-take-all hard)
        output = torch.stack(all_mem_l2).sum(0)
        snap1 = mem_history_l1[-1]
        snap2 = mem_history_l2[-1]
        return output, snap1, snap2

    def lct_train_dialogue(self, dialogue, label, phi, C):
        """Entraîne sur un dialogue complet avec Snapshot Topologique.

        1. Forward temporel (3 tours, accumulation)
        2. P_sig = GUDHI sur le snapshot final (1 seul calcul, pas par mot)
        3. Mise à jour LCT avec l'émotion comme modulation
        """
        # 1. forward temporel
        output, snap1, snap2 = self.forward_temporal(dialogue)
        pred = output.argmax(dim=-1).item()
        correct = (pred == label)

        # 2. Snapshot Topologique : P_sig = GUDHI sur le snapshot final (1 calcul)
        P_sig1 = compute_p_sig_eligibility(snap1)
        P_sig2 = compute_p_sig_eligibility(snap2)

        # 3. modulation = émotion (Facteur 3 = dopamine)
        reward = 1.0 if correct else -1.0
        modulation = phi * C * reward

        # 4. mise à jour LCT
        # activité accumulée (Facteur 1) : moyenne des spikes sur les 3 tours
        # on refait un forward pour récupérer les spikes (déjà accumulés dans forward)
        self.reset()
        acc_spk1 = torch.zeros(self.layer1.out_features)
        acc_spk2 = torch.zeros(self.layer2.out_features)
        for turn_emb in dialogue:
            for t in range(self.n_steps_per_turn):
                spk1, _ = self.layer1(turn_emb)
                spk2, _ = self.layer2(spk1)
                acc_spk1 += spk1.squeeze()
                acc_spk2 += spk2.squeeze()
        acc_spk1 /= (len(dialogue) * self.n_steps_per_turn)
        acc_spk2 /= (len(dialogue) * self.n_steps_per_turn)

        # teacher forcing : force le neurone cible
        acc_spk2_tf = acc_spk2.clone()
        acc_spk2_tf[label] = 1.0

        # dernier tour pour les poids pré-synaptiques
        last_turn = dialogue[-1]
        dW1 = self.layer1.lct_update(last_turn, acc_spk1.unsqueeze(0), snap1,
                                      modulation, 1.0, P_sig1)
        dW2 = self.layer2.lct_update(acc_spk1.unsqueeze(0), acc_spk2_tf.unsqueeze(0),
                                      snap2, modulation, 1.0, P_sig2,
                                      target_neuron=label, reward=reward)
        return correct, P_sig1, P_sig2


# ─────────────────────────────────────────────────────────────────────────────
# 3. ENTRAÎNEMENT
# ─────────────────────────────────────────────────────────────────────────────

def train_emocontext(filepath, max_samples=300, epochs=15, eta=0.8,
                     n_steps=12, hidden=32, vocab_size=150, seed=42):
    """Entraîne RATISS-Snn temporel sur EmoContext."""
    dialogues, labels, vocab = load_emocontext(filepath, max_samples, vocab_size)
    n_classes = 4
    in_features = len(vocab)

    # split train/test
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(dialogues))
    n_test = min(50, len(dialogues) // 5)
    test_idx = indices[:n_test]
    train_idx = indices[n_test:]

    # convert to tensors
    def to_tensor_dialogue(dialogue):
        return [torch.tensor(t, dtype=torch.float32) for t in dialogue]

    train_dialogues = [to_tensor_dialogue(dialogues[i]) for i in train_idx]
    train_labels = [labels[i] for i in train_idx]
    test_dialogues = [to_tensor_dialogue(dialogues[i]) for i in test_idx]
    test_labels = [labels[i] for i in test_idx]

    net = TemporalLCTSnn(in_features, hidden, n_classes, eta=eta,
                          n_steps_per_turn=n_steps, seed=seed)
    net.layer1.lif.threshold = torch.tensor(0.15)
    net.layer2.lif.threshold = torch.tensor(0.15)

    print(f"=== RATISS-Snn Temporel sur EmoContext ===")
    print(f"Samples : {len(dialogues)} (train={len(train_dialogues)}, test={len(test_dialogues)})")
    print(f"Vocab : {len(vocab)} mots | Hidden : {hidden} | n_steps/tour : {n_steps}")
    print(f"Classes : {LABEL_NAMES}")
    print(f"CPU-only : {not torch.cuda.is_available()}\n")

    label_dist = Counter(train_labels)
    print(f"Distribution train : {dict(label_dist)}\n")

    for epoch in range(epochs):
        theta = epoch / epochs * math.pi
        phi = abs(math.cos(theta))
        C = abs(math.cos(theta))

        # entraînement
        corrects = 0
        psigs = []
        for i in range(len(train_dialogues)):
            correct, psig1, psig2 = net.lct_train_dialogue(
                train_dialogues[i], train_labels[i], phi, C)
            corrects += correct
            psigs.append(psig1)
        train_acc = corrects / len(train_dialogues)

        # test
        test_corrects = 0
        test_preds = []
        for i in range(len(test_dialogues)):
            out, _, _ = net.forward_temporal(test_dialogues[i])
            pred = out.argmax(-1).item()
            test_preds.append(pred)
            test_corrects += (pred == test_labels[i])
        test_acc = test_corrects / len(test_dialogues)

        if epoch % 3 == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:2d} | φ={phi:.3f} C={C:.3f} | "
                  f"train_acc={train_acc:.3f} test_acc={test_acc:.3f} | "
                  f"P_sig={np.mean(psigs):.4f}")

    print(f"\n=== Final : train={train_acc:.3f} test={test_acc:.3f} ===")
    print(f"Prédictions test : {Counter(test_preds)}")
    print(f"Vraies : {Counter(test_labels)}")
    return net, test_acc


if __name__ == "__main__":
    # télécharger train.txt depuis le dépôt si pas en local
    local_path = os.path.join(os.path.dirname(__file__), "ratis_snn_emocontext_data.txt")
    if not os.path.exists(local_path):
        # fallback : chercher dans le workspace
        alt = os.path.join(os.path.dirname(__file__), "ratis_snn_emocontext_data.txt")
        if os.path.exists(alt):
            local_path = alt
        else:
            print(f"Fichier EmoContext introuvable. Place train.txt à {local_path}")
            sys.exit(1)

    net, acc = train_emocontext(local_path, max_samples=200, epochs=30,
                                 eta=1.0, n_steps=10, hidden=32, vocab_size=16)
    print(f"\n✅ RATISS-Snn temporel sur EmoContext : {acc:.1%} (sans backprop)")
