from load_nodes import FrameworkLoad
from assembler import MatrixAssembler
from solver import FiniteElementSolver

from pathlib import Path
import os

from InquirerPy import inquirer
import sys


def main():
    """
    Dieses Skript muss ausgeführt werden für den FEM-Solver. Bevor man das Programm start bitte die 'ReadMe.md'-Datei lesen.

    Nach dem Ausführen kann in der Konsole gewählt werden, welches Element geladen und berechnet werden soll. Die Möglichkeiten:

    Kran: 'crane_node_file.xlsx'
    Brücke: 'bridge_node_file.xlsx'
    Turm: 'tower_node_file.xlsx'
    """

    choice = inquirer.select(
        message='Wählen Sie ein Stabwerk zur Modellierung aus:',
        choices=['Model 1: Kran', 'Model 2: Brücke', 'Model 3: Turm'],
    ).execute()

    if choice == 'Model 1: Kran':
        path = 'crane_node_file.xlsx'
    elif choice == 'Model 2: Brücke':
        path = 'bridge_node_file.xlsx'
    elif choice == 'Model 3: Turm':
        path = 'tower_node_file.xlsx'
    else:
        print('Programm wird beendet.')
        sys.exit()

    FILE_NAME = Path(path)

    PATH = Path(os.path.join(Path(r'model_files'), FILE_NAME))

    sheet_names = ('Nodes', 'Elements', 'Forces', 'Boundary_Conditions')

    PATH_solutions = Path(r'model_files/framework_solution.txt')

    load = FrameworkLoad(PATH, sheet_names)
    node_data = load.nodes()
    element_data = load.elements()

    assembler = MatrixAssembler(node_data, element_data)
    K = assembler.stiffness_matrix()

    f = load.forces()

    K_bc, nodes_bc = assembler.boundary_conditions(PATH, K)

    solver = FiniteElementSolver()
    success = solver.solve(K_bc, f, element_data, nodes_bc, PATH_solutions)

    if not success:
        raise ValueError(
            f'An error occured while trying to write the solution file {PATH_solutions}.')
    else:
        print(
            f'The solution has been successfully written to {PATH_solutions}.')

    solver.plot(node_data, element_data, FILE_NAME)


if __name__ == "__main__":
    main()
