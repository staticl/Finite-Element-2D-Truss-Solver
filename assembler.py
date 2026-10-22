import numpy as np
import pandas as pd

from pathlib import Path
import os


class MatrixAssembler:
    """
    This class is used to create the global stiffness matrix of the framework. First it is creating the element-wise
    stiffness matrix in global coordinates and after it assembeles the global stiffness matrix. 
    For that the method 'stiffness_matrix' is used.

    This class also provides the method 'boundary_condtions' which modifies the stiffness matrix based on boundary conditions given
    using the penalty method.
    """

    def __init__(self, node_data: dict, element_data: dict) -> None:
        """
        Saves the 'node_data' dict to 'self.node_data' and the 'element_data' to 'self.element_data',
        and creates the blueprint for the local stiffness matrix. It also initaizes the global node number set.

        Args:
            node_data: dictonary with the node numbers and its corresponding coordinates
            element_data: dictonary with the element-ids, its correspong nodes and the E-Modules and radius of each element
        """
        if len(node_data.keys()) == 0 or len(element_data.keys()) == 0:
            raise ValueError('The framwork data is none.')
        self.node_data = node_data
        self.element_data = element_data

        self.K_e = np.array(
            [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]])

    def stiffness_matrix(self) -> np.ndarray[float]:
        """
        Assembles the global stiffness matrix.

        Returns:
            The global stiffness matrix of size 2*n_nodes x 2*n_nodes
        """
        self._element_stiffness_matrix()

        n_nodes = len(self.node_data.keys())

        K = np.zeros((2 * n_nodes, 2 * n_nodes))

        for i in range(len(self.element_data['Element-ID'])):
            n_start = 2 * self.element_data['Start-Node'][i]
            n_end = 2 * self.element_data['End-Node'][i]
            nodes = [n_start, n_start + 1, n_end, n_end + 1]
            K[np.ix_(nodes, nodes)] += self.element_data['stiffness_matrix'][i]

        return K

    def _element_stiffness_matrix(self) -> None:
        """
        Adds the element stiffness matrix to the 'element_data' dictionaries for each bar. It uses the key: 'stiffness_matrix'.
        """
        self.element_data['stiffness_matrix'] = []
        self.element_data['cos_sin'] = []
        self.element_data['length'] = []

        for i in range(len(self.element_data['Element-ID'])):
            r = self.element_data['Radius'][i]
            p1 = np.array(self.node_data[self.element_data['Start-Node'][i]])
            p2 = np.array(self.node_data[self.element_data['End-Node'][i]])
            area, length, sin_a, cos_a = self._calc_values(r, p1, p2)
            T_e = self._transform_matrix(sin_a, cos_a)
            K_e = T_e @ (self.element_data['E-Module'][i] * area /
                         length * self.K_e) @ T_e.T

            self.element_data['stiffness_matrix'].append(K_e)
            self.element_data['cos_sin'].append((cos_a, sin_a))
            self.element_data['length'].append(length)

        self.element_data['stiffness_matrix'][0]

    def _calc_values(self, r: float, p1: np.ndarray, p2: np.ndarray) -> tuple[float]:
        """
        Calculates the cross-section area, the length, and the sin and cos of the bar.

        Args:
            r: radius of the cross-section area
            p1: coordinates of the first edge point
            p2: coordinates of the second edge point

        Returns:
            A tuple with the area, length, sin(alpha), and cos(alpha) of the bar.
        """
        area = np.pi * r**2
        d = p2 - p1
        length = np.sqrt(np.sum(d**2))
        sin_a = d[1] / length
        cos_a = d[0] / length
        return area, length, sin_a, cos_a

    def _transform_matrix(self, sin_a: float, cos_a) -> np.ndarray:
        """
        Creates the transformation matrix T to transform the transformation matrix into global coordinates.

        Args:
            sin_a: sinus of the angle between local and global coordinate systems
            cos_a: cosinus of the angle between local and global coordinate systems

        Returns:
            transformation matrix of the element
        """
        T_e = np.array([[cos_a, -sin_a, 0, 0], [sin_a, cos_a, 0, 0],
                       [0, 0, cos_a, -sin_a], [0, 0, sin_a, cos_a]])
        return T_e

    def boundary_conditions(self, path: Path, K: np.ndarray) -> tuple[np.ndarray, list]:
        """
        Modifies the indexes of the stiffness matrix on which boundary conditions apply. It sets them to 1e25.

        Args:
            path: path to the main Excel file
            K: the unmodified stiffness matrix

        Returns:
            The modified stiffness matrix based on the boundary conditions.

        Raises:
            IndexError: If the node index of the boundary condition is out of bounds.
            ValueError: If the coordinate direction of locking doesn't exist.
        """
        bc_df = pd.read_excel(
            path, sheet_name='Boundary_Conditions', engine="openpyxl")

        bc_data = bc_df.to_dict(orient='list')
        bc_nodes = []

        for i in range(len(bc_data['Node-ID'])):
            direction = bc_data['Direction'][i]
            if direction == 'X':
                node = 2 * bc_data['Node-ID'][i]
            elif direction == 'Y':
                node = 2 * bc_data['Node-ID'][i] + 1
            else:
                raise ValueError(
                    f"The direction '{direction}' isn't a valid. Only 'X' and 'Y' are valid.")
            if node >= K.shape[1]:
                raise IndexError(f"Node-Index '{node}' is out of bounds.")

            K[node, node] = 1e25
            bc_nodes.append(node)

        return K, bc_nodes
