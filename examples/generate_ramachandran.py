import numpy as np
import matplotlib.pyplot as plt
from Bio.PDB import PDBParser, PPBuilder

def calculate_phi_psi(pdb_file):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('2OCJ', pdb_file)
    ppb = PPBuilder()
    
    phi_psi_data = []
    for model in structure:
        for chain in model:
            for pp in ppb.build_peptides(chain):
                phi_psi = pp.get_phi_psi_list()
                for i, (phi, psi) in enumerate(phi_psi):
                    if phi and psi:
                        phi_psi_data.append((np.degrees(phi), np.degrees(psi)))
    return phi_psi_data

data = calculate_phi_psi('4_computational_solvers/validation_report/TEST_1_PDB_2OCJ_fields/2OCJ.pdb')
phi, psi = zip(*data)

plt.figure(figsize=(8, 8), facecolor='#0b0f19')
ax = plt.gca()
ax.set_facecolor('#0b0f19')
plt.scatter(phi, psi, s=5, c='#4fd1c5', alpha=0.6)
plt.axhline(0, color='white', lw=0.5, alpha=0.3)
plt.axvline(0, color='white', lw=0.5, alpha=0.3)
plt.xlim(-180, 180)
plt.ylim(-180, 180)
plt.xlabel('$\phi$ (phi, °)', color='white')
plt.ylabel('$\psi$ (psi, °)', color='white')
plt.title('Corrected Ramachandran Plot (2OCJ)', color='white')
ax.tick_params(colors='white')
for spine in ax.spines.values():
    spine.set_edgecolor('white')

plt.savefig('figure_7_ramachandran_corrected.png', dpi=150)
