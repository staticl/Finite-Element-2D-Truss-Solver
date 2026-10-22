import pandas as pd
import numpy as np

import os
from pathlib import Path


class FrameworkLoad:
    """
    This class is used to read the framework data from Excel Files to be able to assemble to stiffness matrix and the force vector.
    """

    def __init__(self, path: Path, sheet_names: tuple[str]) -> None:
        """
        Checks if the framework and force file exists, converts the file paths to absolute ones.
        It also saves them as 'self.path_framework', 'self.path_forces' and 'self.path_bc'.

        Args: 
            path: file path to the framework info Excel file
            sheet_names: the required sheet names in the Excel file

        Raises:
            FileNotFoundError: If any of the files can't be found/don't exist.
            ValueError: If the Excel file is completely empty.
            ValueError: If any of the required sheets are not inside the excel file.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(
                f'File with path "{path}" not found.')
        if os.path.isabs(path):
            path = os.path.relpath(path)

        if os.path.getsize(path) == 0:
            raise ValueError(
                f'No data in {os.path.relpath(self.path)}')

        file = pd.ExcelFile(path, engine="openpyxl")
        for sheet in sheet_names:
            if sheet not in file.sheet_names:
                raise ValueError(f"Sheet with name '{sheet}' isn't in {path}")

        self.path = path

    def nodes(self) -> dict:
        """
        Opens the Excel file, reads the 'Nodes' sheet of the Excel file and returns the node data.

        Returns:
            A dictonary with the node ID as keys and it's coordinates as values.
        """
        nodes_df = pd.read_excel(
            self.path, sheet_name='Nodes', engine="openpyxl")
        self.n_nodes = len(nodes_df.index)
        node_data = {}

        for i in range(self.n_nodes):
            this_node = nodes_df.iloc[i]
            node_data[int(this_node['Node-ID'])
                      ] = (this_node['X'], this_node['Y'])

        return node_data

    def elements(self) -> dict:
        """
        Opens the Excel file, reads the 'Elements' sheet of the Excel file and returns the element data.

        Returns:
            A dictonary with the element ID as keys and it's corresponding nodes as values.
        """
        elements_df = pd.read_excel(
            self.path, sheet_name='Elements', engine="openpyxl")

        element_data = elements_df.to_dict(orient='list')

        return element_data

    def forces(self) -> np.ndarray:
        """
        Reads the 'Forces' sheet of the Excel file and creates the force vector f.

        Returns:
            The force vector f as a np.ndarray.

        Raises:
            IndexError: If the node index is out of range.
            ValueError: If the direction of force is in neither x nor y direction.
        """
        f = np.zeros(2 * self.n_nodes)

        force_df = pd.read_excel(
            self.path, sheet_name='Forces', engine="openpyxl")

        nodes, directions, forces = force_df['Node-ID'].to_numpy(
        ), force_df['Direction'].to_numpy(), force_df['Value'].to_numpy()

        for node, direction, force in zip(nodes, directions, forces):
            if node >= self.n_nodes:
                raise IndexError(
                    f'Index {2 * node + 1} is out of range for f of length {2 * self.n_nodes}')
            if direction == 'X':
                f[2 * node] = force
            elif direction == 'Y':
                f[2 * node + 1] = force
            else:
                raise ValueError(
                    f"The direction '{direction}' isn't a valid. Only 'X' and 'Y' are valid.")
        return f
