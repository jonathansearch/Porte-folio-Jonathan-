# Modules Source RATISS (`src/`)

Ce répertoire contient les modules Python natifs qui constituent le cœur logique du système RATISS (Real-time Analysis & Topological Intelligence for Scientific Systems). Ces modules sont conçus pour être importés et utilisés comme des bibliothèques dans des applications plus vastes, plutôt que d'être exécutés directement comme des scripts autonomes.

## Structure des Modules

| Fichier | Description |
| :------ | :---------- |
| `p_vs_np_core_extracted.py` | **Orchestrateur Principal du Solveur Cypher ODV.** Ce module contient la classe `RATISSCypherODVSolver` qui gère le pipeline complet des quatre lois mathématiques fondamentales, l'intégration avec le compresseur topologique et le proveur Zero-Knowledge. Il sert de point d'entrée pour l'exécution des analyses complexes de RATISS. |
| `topology_compressor_native.py` | **Moteur de Compression Topologique CPU-Native.** Ce module implémente la logique de compression de dimensionnalité topologique. Il prend en charge la filtration de Vietoris-Rips, l'homologie persistante, la sparsification spectrale et l'extraction de complexes de cliques, optimisé pour une utilisation CPU avec des contraintes de mémoire strictes. |
| `topozK_prover_native.py` | **Proveur Zero-Knowledge (ZK) CPU-Native.** Ce module fournit l'implémentation d'un proveur ZK pour certifier l'exécution correcte et l'intégrité des résultats du pipeline RATISS. Il est compatible avec les architectures RISC-V/SP1 (via compilation Rust) mais offre une version Python pour l'audit et le débogage.

## Dépendances

Les modules de ce répertoire s'appuient sur les bibliothèques Python suivantes :

-   `numpy` : Pour les opérations numériques et les calculs matriciels.
-   `scipy` : Pour l'algèbre linéaire sparse et les algorithmes graphiques.
-   `psutil` : Pour la surveillance de l'utilisation de la mémoire (dans `topology_compressor_native.py`).
-   `hashlib`, `json`, `time`, `dataclasses`, `typing`, `collections` : Bibliothèques standards Python.

Vous pouvez installer ces dépendances en utilisant le fichier `requirements.txt` à la racine du dépôt :

```bash
pip install -r ../requirements.txt
```

## Utilisation

Pour utiliser ces modules, importez les classes nécessaires dans votre script Python. Par exemple :

```python
from src.p_vs_np_core_extracted import RATISSCypherODVSolver, ProblemInstance

# Créer une instance du solveur
solver = RATISSCypherODVSolver()

# Préparer une instance de problème (exemple)
problem_data = [[0, 1, 2], [1, 0, 3], [2, 3, 0]] # Matrice de distances pour TSP
instance = ProblemInstance(problem_type='TSP_METRIC', size=3, data=problem_data)

# Résoudre le problème
result = solver.solve(instance)

print(f"Statut de la solution : {result.status}")
print(f"Valeur objective : {result.objective_value}")
print(f"Preuve ZK vérifiée : {result.verified}")
```

Des exemples plus concrets d'intégration et d'utilisation sont disponibles dans le répertoire [`examples/`](../examples/).
