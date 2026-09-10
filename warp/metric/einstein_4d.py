"""
warp.metric.einstein_4d — Dérivation tensorielle 4D de la métrique d'Alcubierre.

Calcule, en calcul symbolique (SymPy), la chaîne complète :
    métrique g_μν  →  inverse g^μν  →  Christoffel Γ^λ_μν
    →  Riemann R^ρ_σμν  →  Ricci R_μν  →  Einstein G_μν
    →  tenseur énergie-impulsion requis T_μν = G_μν / (8πG)
    →  densité d'énergie ρ = T_00 (l'exotic matter d'Alcubierre)

Puis injecte le terme Λ_LCT (construit depuis un champ scalaire P(x) = persistance
P_sig interpolée) et calcule le tenseur effectif T_eff = T_standard + T_LCT,
montrant comment Λ_LCT compense l'exotic matter.

Métrique (référentiel comobile, x_s=0, v_s=v constant) :
    ds² = -(1 - v²·f²)·dt² - 2·v·f·dx·dt + dx² + dy² + dz²
avec r_s² = x² + y² + z². f = f(r_s²) est laissée symbolique (Function),
toutes les dérivées s'expriment en f et df/d(r_s²).

Honnêteté : la métrique standard et la chaîne de calcul sont un fait (Alcubierre
1994 + identités tensorielles). Le terme Λ_LCT est l'hypothèse de travail de
Jonathan Evina. La dérivation formelle transforme l'hypothèse en équation de
champ modifiée explicite — mais le verdict « compense l'exotic matter » est
encore conditionnel et validé par le calcul numérique.
"""
from __future__ import annotations

from typing import Dict

import sympy as sp

# ─────────────────────────────────────────────────────────────────────────────
# 1. COORDONNÉES & MÉTRIQUE
# ─────────────────────────────────────────────────────────────────────────────

coords = [sp.Symbol("t", real=True), sp.Symbol("x", real=True),
          sp.Symbol("y", real=True), sp.Symbol("z", real=True)]
t, x, y, z = coords
v = sp.Symbol("v", real=True, positive=True)          # vitesse de la bulle
# f = f(r_s²) — fonction symbolique du rayon carré
rs2 = x**2 + y**2 + z**2
f = sp.Function("f")(rs2)

N = 4  # dimension


def metric_tensor() -> sp.Matrix:
    """g_μν d'Alcubierre (comobile, v constant).

        g = [ -(1-v²f²),  -v·f, 0, 0 ]
            [   -v·f,       1,  0, 0 ]
            [    0,         0,  1, 0 ]
            [    0,         0,  0,  1 ]
    """
    g = sp.zeros(N)
    g[0, 0] = -(1 - v**2 * f**2)
    g[0, 1] = -v * f
    g[1, 0] = -v * f
    g[1, 1] = 1
    g[2, 2] = 1
    g[3, 3] = 1
    return g


def metric_inverse() -> sp.Matrix:
    """g^μν. Pour Alcubierre, det(g) = -1 (constant !)."""
    g = metric_tensor()
    return g.inv()


def metric_determinant() -> sp.Expr:
    """det(g) — vaut -1 (astuce d'Alcubierre : volume préservé)."""
    return sp.simplify(metric_tensor().det())


# ─────────────────────────────────────────────────────────────────────────────
# 2. SYMBOLES DE CHRISTOFFEL
# ─────────────────────────────────────────────────────────────────────────────

def christoffel() -> Dict:
    """Γ^λ_μν = ½ g^λσ (∂_μ g_νσ + ∂_ν g_μσ - ∂_σ g_μν).

    Retourne un dict {(lamb, mu, nu): expr} des composantes non-nulles.
    f(r_s²) contraint la topologie du mur.
    """
    g = metric_tensor()
    g_inv = g_inv_cache = sp.simplify(g.inv())
    # précalcul des dérivées ∂_σ g_μν
    dg = {}
    for sigma in range(N):
        for mu in range(N):
            for nu in range(N):
                dg[(sigma, mu, nu)] = sp.diff(g[mu, nu], coords[sigma])

    gamma = {}
    for lam in range(N):
        for mu in range(N):
            for nu in range(mu, N):  # symétrie μ↔ν
                val = 0
                for sigma in range(N):
                    val += g_inv[lam, sigma] * (
                        dg[(mu, nu, sigma)] + dg[(nu, mu, sigma)] - dg[(sigma, mu, nu)]
                    )
                val = sp.simplify(val / 2)
                if val != 0:
                    gamma[(lam, mu, nu)] = val
                    if mu != nu:
                        gamma[(lam, nu, mu)] = val
    return gamma


# ─────────────────────────────────────────────────────────────────────────────
# 3. RIEMANN → RICCI → EINSTEIN
# ─────────────────────────────────────────────────────────────────────────────

def riemann_ricci_einstein(gamma: Dict | None = None,
                            simplify_level: int = 1) -> Dict:
    """Calcule Riemann, Ricci, scalaire de courbure, Einstein G_μν.

    R^ρ_σμν = ∂_μ Γ^ρ_νσ - ∂_ν Γ^ρ_μσ + Γ^ρ_μλ Γ^λ_νσ - Γ^ρ_νλ Γ^λ_μσ
    R_σν = R^ρ_σρν   (contraction sur ρ=premier, μ=ρ)
    R = g^σν R_σν
    G_μν = R_μν - ½ R g_μν

    simplify_level : 0 = pas de simplify (rapide), 1 = simplify, 2 = trigsimp.
    Retourne un dict {riemann, ricci, scalar, einstein} (composantes non-nulles).

    ⚠️ Le calcul complet de Riemann (4D, 256 composantes) est lourd. On calcule
    directement le Ricci via la contraction (plus rapide) pour les composantes
    dont on a besoin (surtout R_00 = densité d'énergie).
    """
    if gamma is None:
        gamma = christoffel()

    def G(lam, mu, nu):
        return gamma.get((lam, mu, nu), sp.Integer(0))

    coords_local = coords
    # Ricci directement : R_σν = ∂_ρ Γ^ρ_νσ - ∂_ν Γ^ρ_ρσ
    #                      + Γ^ρ_ρλ Γ^λ_νσ - Γ^ρ_νλ Γ^λ_ρσ
    ricci = {}
    for sigma in range(N):
        for nu in range(sigma, N):
            val = 0
            for rho in range(N):
                # ∂_ρ Γ^ρ_νσ
                term1 = sp.diff(G(rho, nu, sigma), coords_local[rho])
                # Γ^ρ_ρλ Γ^λ_νσ
                term3 = 0
                for lam in range(N):
                    term3 += G(rho, rho, lam) * G(lam, nu, sigma)
                # - Γ^ρ_νλ Γ^λ_ρσ
                term4 = 0
                for lam in range(N):
                    term4 -= G(rho, nu, lam) * G(lam, rho, sigma)
                val += term1 + term3 + term4
            # - ∂_ν Γ^ρ_ρσ
            for rho in range(N):
                val -= sp.diff(G(rho, rho, sigma), coords_local[nu])
            if simplify_level == 1:
                val = sp.simplify(val)
            elif simplify_level == 2:
                val = sp.trigsimp(sp.simplify(val))
            if val != 0:
                ricci[(sigma, nu)] = val
                if sigma != nu:
                    ricci[(nu, sigma)] = val

    # scalaire R = g^σν R_σν
    g_inv = sp.simplify(metric_tensor().inv())
    R = 0
    for sigma in range(N):
        for nu in range(N):
            R += g_inv[sigma, nu] * ricci.get((sigma, nu), sp.Integer(0))
    R = sp.simplify(R)

    # Einstein G_μν = R_μν - ½ R g_μν
    g = metric_tensor()
    einstein = {}
    for mu in range(N):
        for nu in range(mu, N):
            val = ricci.get((mu, nu), sp.Integer(0)) - R * g[mu, nu] / 2
            val = sp.simplify(val)
            if val != 0:
                einstein[(mu, nu)] = val
                if mu != nu:
                    einstein[(nu, mu)] = val

    return {"ricci": ricci, "scalar": R, "einstein": einstein}


# ─────────────────────────────────────────────────────────────────────────────
# 4. TENSEUR ÉNERGIE-IMPULSION REQUIS + EXOTIC MATTER
# ─────────────────────────────────────────────────────────────────────────────

def stress_energy_required(einstein: Dict | None = None,
                            G_newton: sp.Symbol | None = None) -> Dict:
    """T_μν = G_μν / (8πG). Le tenseur requis par la métrique.

    ρ = T_00 est l'exotic matter d'Alcubierre (négative dans le mur).
    """
    if einstein is None:
        einstein = riemann_ricci_einstein()["einstein"]
    if G_newton is None:
        G_newton = sp.Symbol("G", positive=True)
    factor = 1 / (8 * sp.pi * G_newton)
    T = {}
    for k, val in einstein.items():
        T[k] = sp.simplify(factor * val)
    return T


# ─────────────────────────────────────────────────────────────────────────────
# 5. TERME Λ_LCT (3 ansatz, construits depuis un champ scalaire P)
# ─────────────────────────────────────────────────────────────────────────────

def lambda_lct_tensor(ansatz: str = "kinetic",
                      kappa: sp.Symbol | None = None,
                      P_field: sp.Expr | None = None) -> sp.Matrix:
    """Tenseur Λ_LCT_μν construit depuis un champ scalaire P(x) = persistance.

    ansatz :
      kinetic  : Λ_μν = -κ ∇_μ P ∇_ν P            (énergie topologique positive)
      local_cc : Λ_μν = -κ □P g_μν                (constante cosmologique locale)
      pressure : Λ_μν = +κ P g_μν                 (pression directe)
    """
    if kappa is None:
        kappa = sp.Symbol("kappa", real=True)
    if P_field is None:
        P_field = sp.Function("P")(x, y, z)   # P_sig interpolée

    g = metric_tensor()
    g_inv = sp.simplify(g.inv())
    lam = sp.zeros(N)

    if ansatz == "kinetic":
        for mu in range(N):
            for nu in range(N):
                dPmu = sp.diff(P_field, coords[mu])
                dPnu = sp.diff(P_field, coords[nu])
                lam[mu, nu] = -kappa * dPmu * dPnu
    elif ansatz == "local_cc":
        # □P = g^μν ∇_μ∇_ν P  (approximation des dérivées secondes covariantes ≈ partielles)
        boxP = 0
        for mu in range(N):
            for nu in range(N):
                boxP += g_inv[mu, nu] * sp.diff(P_field, coords[mu], coords[nu])
        for mu in range(N):
            for nu in range(N):
                lam[mu, nu] = -kappa * boxP * g[mu, nu]
    elif ansatz == "pressure":
        for mu in range(N):
            for nu in range(N):
                lam[mu, nu] = kappa * P_field * g[mu, nu]
    elif ansatz == "canonical":
        # Tenseur énergie-impulsion d'un champ scalaire CANONIQUE :
        #   Λ_μν = κ [∇_μP ∇_νP - ½ g_μν (∇P)²]
        # Pour P stationnaire : Λ_00 = ½(1-v²f²)(∇P)²·κ > 0 → COMPENSE T_00 < 0.
        # Physiquement sain (pas un ghost) : énergie cinétique positive.
        gpn2 = 0
        for a in range(N):
            for b in range(N):
                gpn2 += g_inv[a, b] * sp.diff(P_field, coords[a]) * sp.diff(P_field, coords[b])
        for mu in range(N):
            for nu in range(N):
                lam[mu, nu] = kappa * (sp.diff(P_field, coords[mu]) * sp.diff(P_field, coords[nu])
                                        - sp.Rational(1, 2) * g[mu, nu] * gpn2)
    else:
        raise ValueError(ansatz)
    return sp.simplify(lam)


def effective_stress_energy(T_standard: Dict, lam: sp.Matrix,
                             G_newton: sp.Symbol | None = None) -> sp.Matrix:
    """T_eff_μν = T_standard_μν + T_LCT_μν, où T_LCT = -Λ_LCT / (8πG).

    G_μν + Λ_LCT_μν = 8πG T_eff  ⇒  T_eff = (G + Λ)/(8πG) = T_std + Λ/(8πG).
    ATTENTION au signe : l'équation modifiée est G + Λ = 8πG T_eff, donc
    T_eff = T_std + Λ/(8πG). Si Λ_00 > 0 (kinetic), T_eff_00 augmente (compense ρ<0).
    """
    if G_newton is None:
        G_newton = sp.Symbol("G", positive=True)
    factor = 1 / (8 * sp.pi * G_newton)
    T_eff = sp.zeros(N)
    for mu in range(N):
        for nu in range(N):
            Ts = T_standard.get((mu, nu), sp.Integer(0))
            T_eff[mu, nu] = sp.simplify(Ts + lam[mu, nu] * factor)
    return T_eff


if __name__ == "__main__":
    print("=== Métrique d'Alcubierre 4D ===")
    g = metric_tensor()
    sp.pprint(g)
    print("\ndet(g) =", metric_determinant())
    print("\n=== Inverse g^μν ===")
    sp.pprint(metric_inverse())

    print("\n=== Christoffel (composantes non-nulles) ===")
    gamma = christoffel()
    for k in sorted(gamma.keys()):
        print(f"  Γ^{k[0]}_{k[1]}{k[2]} =", sp.simplify(gamma[k]))
