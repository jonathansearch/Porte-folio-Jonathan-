import numpy as np

def parse_pdb_com(filename):
    chains = {}
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('ATOM'):
                chain = line[21]
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                if chain not in chains:
                    chains[chain] = []
                chains[chain].append(np.array([x, y, z]))
    
    coms = {c: np.mean(coords, axis=0) for c, coords in chains.items()}
    return coms

coms = parse_pdb_com('4_computational_solvers/validation_report/TEST_1_PDB_2OCJ_fields/2OCJ.pdb')
keys = sorted(coms.keys())
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        c1, c2 = keys[i], keys[j]
        dist = np.linalg.norm(coms[c1] - coms[c2])
        print(f"Distance between COM of Chain {c1} and {c2}: {dist:.2f} A")
