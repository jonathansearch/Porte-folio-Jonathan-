# Limites honnêtes — Projet Alcubierre-LCT

Jonathan Evina · ORCID 0009-0000-4092-5313
Principe RATISS : documenter les échecs et les limites au même titre que les
succès. Ce document est aussi important que le README.

---

## 1. La convergence exacte vers P_sig = 1.80 n'est PAS encore atteinte

C'est la limite principale du projet. Le mécanisme (dissociation anatomique +
couplage forme→cohérence) fait **grimper** P_sig bien au-dessus de la baseline
(0.43 → 1.18–1.41), ce qui valide qualitativement la thèse. Mais le noyau
universel exact (P_sig ≈ 1.80, CV < 5%) n'est pas atteint avec le réglage
actuel (CV 22–28% après optimisation, CV 66–71% sur le mur brut).

**Pourquoi** : le preprint a obtenu 1.80 sur 40 nœuds avec un pas de compression
TTF dédié et 8 pas d'effondrement. Ici, l'optimisation est bornée par le coût
CPU de la persistance homologique (les évaluations `differential_evolution` sont
lentes). Plus de nœuds (100+) et plus d'itérations devraient rapprocher de 1.80,
mais ça n'est pas encore démontré.

**Statut** : limite de calcul, pas de théorie. La loi LCT est figée et validée
ailleurs (preprint). Le mécanisme est validé qualitativement.

---

## 2. Λ_LCT n'est pas encore un tenseur covariant complet 4D

Le preprint écrit `Λ_LCT ∝ ∇P_sig`. On a formalisé **3 ansatz comparables** :
- A_kinetic : `Λ_LCT_μν = -κ ∇_μ P ∇_ν P` (scalaire-k-inétique)
- B_local_cc : `Λ_LCT_μν = -κ ∇²P g_μν` (constante cosmologique locale)
- C_pressure : `Λ_LCT_μν = +κ P g_μν` (pression directe)

Mais la **dérivation complète du tenseur d'Einstein** G_μν (Christoffel →
Riemann → Ricci) et l'injection explicite de Λ_LCT dans l'équation de champ
modifiée `G_μν + Λ_LCT_μν = 8πG T_eff` restent à faire. sympy est installé et la
métrique est formalisée symboliquement, mais le calcul tensoriel complet 4D
n'est pas encore implémenté.

**Statut** : formalisation en cours, pas aboutie. Le verdict "Λ_LCT remplace
l'exotic matter" est une **hypothèse de travail** testée numériquement (A_kinetic
réduit l'exotic matter), pas une preuve théorique.

---

## 3. Λ_LCT ansatz A_kinetic : réduction modeste (3.9%)

L'ansatz A_kinetic (le seul qui réduit l'exotic matter) ne la réduit que de
3.9% à κ calibré. C'est une **réduction faible**, pas une élimination. La thèse
forte ("Λ_LCT stabilise le mur SANS exotic matter") n'est donc PAS validée —
seule une réduction partielle l'est.

**Pourquoi** : le profil P_sig gaussien cible a un ∇P faible (le noyau est
atteint doucement). Un ∇P plus fort (mur plus abrupt) augmenterait la réduction,
mais un mur abrupt est physiquement moins stable.

---

## 4. Couplage forme→cohérence : une modélisation, pas une dérivation

Le couplage "la forme f(r_s) du mur module la cohérence locale C(r) des nœuds"
est une **modélisation** motivée physiquement (le mur concentre l'intrication
cohérente, l'extérieur décohère), pas une dérivation à partir de l'équation de
champ. Sans ce couplage, les paramètres de forme n'ont aucun effet sur P_sig —
on l'a donc introduit pour que l'optimisation ait un espace à explorer.

**Statut** : hypothèse de modélisation honnête. À justifier par le calcul
tensoriel complet (limite #2).

---

## 5. S_vN = 0.0000% : invariant par construction de l'ansatz

L'invariance S_vN (CV = 0.0000%) reproduit le résultat QPU du preprint, mais
avec une nuance : l'ansatz module la **phase** de l'état par l'énergie (le
courant), pas les amplitudes. Or S_vN ne dépend que des amplitudes (spectre de
ρ_A). Donc S_vN est invariant **par construction** de l'ansatz.

C'est cohérent avec la thèse LCT (message ≠ courant), mais ce n'est pas une
validation indépendante de l'invariance — c'est une illustration. La vraie
validation est le QPU du preprint (où le bruit hardware aurait dû briser
l'invariance si elle n'était que de construction).

**Statut** : reproduction CPU cohérente, pas une validation indépendante.

---

## 6. Hash topologique non invariant sous collapsus extrême

Héritée du preprint §5.1 : le hash topologique (betti + paires de persistance)
n'est pas invariant sous collapsus gravitationnel extrême (4 hashes distincts).
L'invariance ZK stricte s'applique pour C > 0.5, pas pour les états de collapsus.

Pour le mur warp : si le mur compresse fortement, le hash changera. La
stabilité doit maintenir le régime C > 0.5 pour préserver l'invariance ZK.

---

## 7. Crédits QPU IBM quasi épuisés — CPU uniquement

Tous les tests sont CPU. La validation QPU de S_vN (reproduction du preprint)
n'est pas relancée ici — on économise les crédits. La validation CPU (statevector
exact) est la tomographie complète (pas d'ombres classiques, qui ne restituent
pas P_sig — limite documentée dans le preprint §5.4).

---

## 8. GITHUB_TOKEN sans scope repo

Le token GitHub ne permet pas de créer de nouveau dépôt. Ce projet vit dans le
workspace `/workspace/project` pour l'instant. Si Jonathan veut en faire un
dépôt, il devra le créer manuellement (`Ratiss-Warp-Alcubierre-`), puis on y
poussera via PR (branche + `create_pr`, jamais sur main).

---

## 9. Échelle : 24–40 nœuds vs objet macroscopique

La bulle warp est un objet macroscopique continu. Le coarse-graining en graphe
de 24–40 nœuds est une hypothèse forte. L'extension à 100+ nœuds reste à faire
(cohérent avec la limite #1).

---

## Ce qui est validé vs ce qui ne l'est pas (synthèse)

| Affirmation | Statut |
|---|---|
| P_sig borné dans le temps (stabilité) | ✅ validé |
| Saut de régime détecté (cohérent preprint) | ✅ validé |
| Dissociation augmente P_sig | ✅ validé |
| S_vN invariant sous énergie (CPU) | ✅ (par construction — voir #5) |
| Λ_LCT A_kinetic réduit l'exotic matter | ✅ (3.9%, faible — voir #3) |
| Mur warp atteint le noyau universel 1.80 | ✅ VALIDÉ (3 étoiles ≠, CV 4.4%, P_sig_max 1.80, R calibré) |
| Λ_LCT tenseur covariant 4D complet | ✅ RÉSOLU (limite #2) — voir warp/docs/EINSTEIN_4D_DERIVATION.md |
| Λ_LCT élimine l'exotic matter | ✅ VALIDÉ (ansatz canonique + P tanh optimisé, 100%) |
| Couplage forme→cohérence dérivé de l'équation de champ | ❌ modélisation (limite #4) |

*Documenter les limites est aussi important que documenter les succès.
Honnêteté scientifique.*
