import numpy as np
import networkx as nx
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import Delaunay
from shapely.geometry import LineString
from sklearn.neighbors import KDTree

import configs
from network import Network


class Grid:
    """
    Класс для создания сетки на плоскости.
    """

    def __init__(self, terminal_points: np.ndarray, quarries_indices: set):

        self.terminal_points = terminal_points
        self.quarries_indices = quarries_indices

        self.lower_left = np.min(terminal_points, axis=0)
        self.upper_right = np.max(terminal_points, axis=0)

        self.points = None
        self.kd_tree = None
        self.connectivity_matrix = None
        self.distance_matrix = None
        self.predecessors = None

    def generate(self):
        """
        Генерация графа сетки.

        :return:
        """
        indent = np.array((configs.BOUNDARY_INDENT, configs.BOUNDARY_INDENT))
        self.points = np.random.uniform(self.lower_left - indent, self.upper_right + indent, size=(configs.GRID_SIZE, 2))
        self.points = np.vstack((self.terminal_points, self.points))

        self.kd_tree = KDTree(self.points)
        distances, indices = self.kd_tree.query(self.points, k=configs.N_GRID_NEIGHBOURS)

        # self.connectivity_matrix = np.zeros((self.points.shape[0], self.points.shape[0]))
        # for ind, neighbours, dists in zip(range(self.points.shape[0]), indices, distances):
        #     self.connectivity_matrix[ind, neighbours] = dists
        #
        # self.connectivity_matrix = np.max(np.dstack((self.connectivity_matrix, self.connectivity_matrix.T)), axis=2)
        tri = Delaunay(self.points)
        indices, indptr = tri.vertex_neighbor_vertices
        self.connectivity_matrix = np.zeros((self.points.shape[0], self.points.shape[0]))
        for ind in range(len(self.points)):
            neighbours = indptr[indices[ind]:indices[ind + 1]]
            vectors = self.points[ind].reshape(1, -1).T - self.points[neighbours].T
            distances = np.linalg.norm(vectors, axis=0)
            self.connectivity_matrix[ind, neighbours] = distances
        self.distance_matrix, self.predecessors = dijkstra(self.connectivity_matrix, return_predecessors=True)

    def reconstruct_path(self, u, v):
        """
        Восстановленный путь от вершины u до вершины v в виде LineString

        :param u:
        :param v:
        :return:
        """
        assert u != v

        points = list()
        while u != v:
            points.append(self.points[v])
            v = self.predecessors[u, v]
        points.append(self.points[u])

        return LineString(reversed(points))

    def create_network(self, graph: nx.Graph):
        """
        Создание сети на основе переданного графа.

        :return:
        """

        vertices = list(graph.nodes)
        quarry_capacities = {ind: 1e2 for ind in self.quarries_indices}

        incidence_list = list()
        for u, v in graph.edges:
            line = self.reconstruct_path(u, v)
            incidence_list.append((u, v, line))

        network = Network(vertices=vertices, quarry_capacities=quarry_capacities, incidence_list=incidence_list)

        return network
