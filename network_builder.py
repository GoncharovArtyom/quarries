import copy

import networkx as nx
import numpy as np

import configs
import utils
from edges_splitter import EdgesSplitter
from grid import Grid
from network import Network

COST_TO_USE = "quarry_cost"

class NetworkBuilder:
    """
    Класс, отвечающий за построение дорожной сети.
    """

    def __init__(self, grid: Grid):

        self.grid = grid

        self._choose_steiner_points()

    def _choose_steiner_points(self):
        """
        Выбор 'точек Штейнера'

        :return:
        """

        x = np.linspace(self.grid.lower_left[0], self.grid.upper_right[0], int(np.sqrt(configs.N_STEINER_POINTS)))
        y = np.linspace(self.grid.lower_left[1], self.grid.upper_right[1], int(np.sqrt(configs.N_STEINER_POINTS)))

        xv, yv = np.meshgrid(x, y)

        steiner_points = np.vstack((xv.flatten(), yv.flatten())).T
        _, steiner_indices = self.grid.kd_tree.query(steiner_points, k=1)

        self.steiner_indices = steiner_indices.flatten()

    def _create_initial_graph(self):
        """
        Полный граф, соержащий только терминальные вершины.

        :return:
        """

        graph = nx.Graph()
        for ind, point in enumerate(self.grid.terminal_points):
            graph.add_node(ind, point=point)

        for ind1 in range(len(self.grid.terminal_points)):
            for ind2 in range(ind1 + 1, len(self.grid.terminal_points)):
                graph.add_edge(ind1, ind2, length=self.grid.distance_matrix[ind1, ind2])

        return graph

    def _build_mst(self):
        """
        Построение оптимального MST.

        :return:
        """
        optimal_graph = self._create_initial_graph()

        network = self.grid.create_network(optimal_graph)
        splitter = EdgesSplitter(network)
        splitter.calculate()
        utils.assign_quarries_costs(network, optimal_graph)

        optimal_mst = nx.minimum_spanning_tree(optimal_graph, weight=COST_TO_USE)
        optimal_cost = optimal_mst.size(weight=COST_TO_USE)

        for _ in range(configs.N_STEINER_POINTS):
            min_current_cost = None
            min_current_mst = None
            min_current_graph = None
            for steiner_point_ind in self.steiner_indices:
                if steiner_point_ind in optimal_graph.nodes:
                    continue

                current_graph = copy.deepcopy(optimal_graph)
                current_graph.add_node(steiner_point_ind)
                for ind, distance in enumerate(self.grid.distance_matrix[steiner_point_ind]):
                    if ind in current_graph.nodes and not np.isclose(distance, 0):
                        current_graph.add_edge(steiner_point_ind, ind, length=distance)

                network = self.grid.create_network(current_graph)
                splitter = EdgesSplitter(network)
                splitter.calculate()
                utils.assign_quarries_costs(network, current_graph)

                current_mst = nx.minimum_spanning_tree(current_graph, weight=COST_TO_USE)
                current_cost = current_mst.size(weight=COST_TO_USE)
                if min_current_cost is None or current_cost < min_current_cost:
                    min_current_cost = current_cost
                    min_current_mst = current_mst
                    min_current_graph = current_graph

            if min_current_cost >= optimal_cost:
                break
            else:
                optimal_cost = min_current_cost
                optimal_mst = min_current_mst
                optimal_graph = min_current_graph

        print(optimal_cost)
        return optimal_mst, optimal_cost

    def build_network(self):
        """
        Получение сети на основе оптимального MST.

        :return:
        """

        mst, cost = self._build_mst()

        network = self.grid.create_network(mst)

        return network
