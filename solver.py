import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from pathlib import Path


class FiniteElementSolver:
    """
    This class solves the system of linear equations 'K @ u = f'. Once the node shifts are calculated it uses them to further calculate
    the stresses and shifts of each bar in the framework.
    
    This class is also able to plot the deformed state of the framework using the 'plot' method.
    """
    def __init__(self) -> None:
        """
        Sets 'self.shifts', 'self.strains' and 'self.stresses' to None. This is used so that the plot method can only be used once
        these values have been calculated.
        """
        self.shifts = None
        self.strains = None
        self.stresses = None

    def solve(self, K: np.ndarray, f: np.ndarray, element_data: dict, nodes_bc: list, path: Path) -> bool:
        """
        This method solves:
        For the node shifts with 'K @ u = f'
        For the element strains with 'ε = D dot u'
        For the elment stresses with 'σ = E @ ε'
        For the boundary foreces with 'f_boundary = -(K_boundary * u_boundary)'

        Args:
            K: The stiffness matrix of the system
            f: The force vector of the system
            element_data: dictonary with the element-ids, its correspong nodes and the E-Modules and radius of each element
            nodes_bc: the node indicies which are blocked by boundary conditions
            path: the path to the result file
        
        Returns:
            True if the text file has been created else False
        """
        self.shifts = np.linalg.solve(K, f)
        strains = []
        stresses = []

        for i in range(len(element_data['Element-ID'])):
            cos_a, sin_a = element_data['cos_sin'][i]
            l = element_data['length'][i]
            n_start = 2 * element_data['Start-Node'][i]
            n_end = 2 * element_data['End-Node'][i]

            nodes = np.array([n_start, n_start + 1, n_end, n_end + 1])

            u = self.shifts[nodes]

            D = 1/l * np.array([-cos_a, -sin_a, cos_a, sin_a])
            strain = np.dot(D, u)
            strains.append(strain)

            # stress = element_data['E-Module'][i] * strain
            stress = element_data['E-Module'][i] * strain
            stresses.append(stress)

        self.strains = strains
        self.stresses = stresses

        self.boundary_forces = self._boundary_forces(K, self.shifts, nodes_bc)

        write = self._write_out_txt(path)

        # self._tables()

        return write

    def _write_out_txt(self, path: Path) -> bool:
        """
        This method writes the calculated values into the 'framework_solution' Text-File. The file gets created in the 'model_files'
        folder.

        Args:
            path: path to model_files/framework_solution.txt
        """
        with open(path, 'w') as output_file:
            t = (self.shifts, self.stresses, self.strains, self.boundary_forces)
            for i in range(len(t)):
                if i == 0:
                    output_file.write('Knotenverschiebungen u in m\n')
                elif i == 1:
                    output_file.write(
                        'Normalspannungen in den Stäben in N/m^2\n')
                elif i == 2:
                    output_file.write('Verzerrungen in den Stäben\n')
                elif i == 3:
                    output_file.write('Reaktionskräfte in den Knoten in N\n')

                for j in range(len(t[i])):
                    if i == 0:
                        if j % 2 == 0:
                            output_file.write(f'Knoten {j // 2}x: {t[i][j]}\n')
                        else:
                            output_file.write(
                                f'Knoten {(j - 1) // 2}y: {t[i][j]}\n')
                            m = np.sqrt(t[i][j-1]**2 + t[i][j]**2)
                            output_file.write(
                                f'Magnitude im Knoten {(j - 1) // 2}: {m}\n')
                    elif i == 1 or i == 2:
                        output_file.write(f'Stabelement {j}: {t[i][j]}\n')
                    elif i == 3:
                        n, f = t[i][j]
                        if n % 2 == 0:
                            output_file.write(
                                f'Knoten {n} in X-Richtung: {f}\n')
                        else:
                            output_file.write(
                                f'Knoten {n - 1} in Y-Richtung: {f}\n')
                            
                output_file.write('\n')

        return True

    def _tables(self) -> None:
        """
        Not used

        It writes the solutions to the 'solutions.xlsx' Excel file. This makes it easier to further work with the calculated values.
        """
        path = r"model_files/solutions.xlsx"
        s = self.shifts.reshape(-1, 2)
        x, y = np.split(s, 2, axis=1)
        m = np.sqrt(x**2 + y**2)
        idx_u = np.arange(len(m)).astype(int)
        df_u = pd.DataFrame(data=m, index=idx_u, columns=['U-Magnitude'])

        idx_s = np.arange(len(self.stresses)).astype(int)
        b = list(zip(*[self.stresses, self.strains]))
        a = np.array(b).reshape(-1, 2)
        df_s = pd.DataFrame(a, index=idx_s, columns=['S_Mises', 'Verzerrung'])
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df_u.to_excel(writer, sheet_name='Verschiebungen')
            df_s.to_excel(writer, sheet_name='Spannungen_Verzerrungen')

    def _boundary_forces(self, K: np.ndarray, u: np.ndarray, nodes_bc: list) -> list[tuple[int, float]]:
        """
        This method calculates the boundary forces using 'f_boundary = -(K_boundary * u_boundary).

        Args:
            K: The stiffness matrix of the system
            u: The node shifts of the system
            nodes_bc: The indicies of the nodes that are part of the boundary conditions
        """
        bc_f = []
        for node in nodes_bc:
            f = -1 * K[node, node] * u[node]
            bc_f.append((node, f))

        return bc_f

    def plot(self, node_data: dict, element_data: dict, file_name: Path) -> None:
        """
        This plots the deformed state relative to it's origional state scaled by the value of scale_factor. It also colours the system
        based on the value of the normla stress in each bar.

        Args:
            node_data: dictonary with the node numbers and its corresponding coordinates
            element_data: dictonary with the element-ids, its correspong nodes and the E-Modules and radius of each element
            file_name: the file name of the used element
        
        Raises:
            ValueError: If the 'solve' method hasn't been called yet.
        """
        scale_factors = { # hier weiteren Werte für andere Elemente einfügen
            'bridge_node_file.xlsx' : 1e4,
            'crane_node_file.xlsx' : 20,
            'tower_node_file.xlsx' : 1.487e3
        }

        scale_factor = scale_factors[str(file_name)]

        if (self.shifts is None or self.stresses is None or self.strains is None):
            raise ValueError(
                "The framework changes haven't been calculated yet. Use the 'solve' method first.")

        node_coords = np.array([item[1] for item in node_data.items()])
        element_nodes = np.array([(a, b) for a, b in zip(
            element_data['Start-Node'], element_data['End-Node'])])
        displacement = np.column_stack((self.shifts[0::2], self.shifts[1::2]))

        nodes_def = node_coords + scale_factor * displacement

        seg_orig = np.array([node_coords[node] for node in element_nodes])
        seg_def = np.array([nodes_def[node] for node in element_nodes])

        _, ax = plt.subplots(figsize=(8, 6))

        orig_coll = LineCollection(
            seg_orig, colors='lightgray', linestyle='dashed', linewidths=1)

        ax.add_collection(orig_coll)

        def_coll = LineCollection(
            seg_def, array=self.stresses, cmap='coolwarm', linewidth=2.5)

        ax.add_collection(def_coll)

        cbar = plt.colorbar(def_coll, ax=ax, orientation='vertical', pad=0.05)
        cbar.set_label(r'Normalspannung $\sigma$ in N/m2', fontsize=11, fontweight='bold')
        
        ax.set_title(f'Verformtes Stabwerk (Skalierungsfaktor: {scale_factor}x)', fontsize=12, fontweight='bold', pad=15)
        ax.set_xlabel('X-Koordinate [m]', fontsize=10)
        ax.set_ylabel('Y-Koordinate [m]', fontsize=10)

        ax.grid(True, linestyle=':', alpha=0.5)

        ax.autoscale_view()
        ax.set_aspect('equal')

        plt.show()
