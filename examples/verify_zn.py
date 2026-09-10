import numpy as np

def get_distance(p1, p2):
    return np.linalg.norm(p1 - p2)

def parse_pdb(filename):
    atoms = []
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('ATOM') or line.startswith('HETATM'):
                atom_name = line[12:16].strip()
                res_name = line[17:20].strip()
                chain = line[21]
                res_seq = int(line[22:26])
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                atoms.append({'name': atom_name, 'res': res_name, 'chain': chain, 'seq': res_seq, 'coord': np.array([x, y, z])})
    return atoms

atoms = parse_pdb('4_computational_solvers/validation_report/TEST_1_PDB_2OCJ_fields/2OCJ.pdb')
zns = [a for a in atoms if a['name'] == 'ZN']

for zn in zns:
    print(f"Zinc ion in chain {zn['chain']} at {zn['coord']}")
    partners = [
        (176, 'SG', 'CYS'),
        (179, 'ND1', 'HIS'),
        (238, 'SG', 'CYS'),
        (242, 'SG', 'CYS')
    ]
    for seq, name, res in partners:
        target = [a for a in atoms if a['chain'] == zn['chain'] and a['seq'] == seq and a['name'] == name]
        if target:
            dist = get_distance(zn['coord'], target[0]['coord'])
            print(f"  Distance to {res}{seq} ({name}): {dist:.2f} A")
