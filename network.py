"""
Класс, объединяющий в себе логику работы с графом.
"""

from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, FrozenSet, DefaultDict

import networkx as nx
import numpy as np
import shapely.wkt as wkt
from shapely.geometry import Point, LineString

import utils
from utils import edge_key


class Network:
    """
    Класс, объединяющий в себе логику работы с графом.
    """

    def __init__(self,
                 vertices: List[int],
                 quarry_capacities: Dict[int, float],
                 incidence_list: List[Tuple[int, int, LineString]]):
        """

        :param vertices: Идентификаторы вершин.
        :param quarry_capacities: Объем материалов доступный для каждого из карьеров. Ключи - вершины, являющиеся карьерами.
        :param incidence_list: Список смежности. LineString - ломаная, соответствующая положению ребра на плоскости,
        при этом первая точка ломанной соответствует первой вершине, а вторая - второй.
        """

        self.quarries = set(quarry_capacities.keys())
        self.usual_vertices = set(vertices) - self.quarries
        self.quarries_capacities = dict(quarry_capacities)

        self.graph = nx.Graph()
        for vertex in vertices:
            self.graph.add_node(vertex)
        self.available_vertex_id = max(vertices)

        self.first_poit_vertex = dict()
        self.last_point_vertex = dict()
        self.vertex_to_point_mapping = dict()
        self.edge_to_line_mapping = dict()
        for u, v, line in incidence_list:
            self.graph.add_edge(u, v, weight=line.length)
            self.first_poit_vertex[edge_key(u, v)] = u
            self.last_point_vertex[edge_key(u, v)] = v

            if u in self.vertex_to_point_mapping:
                utils.assert_points_are_close(self.vertex_to_point_mapping[u], Point(line.coords[0]))
            self.vertex_to_point_mapping[u] = Point(line.coords[0])

            if v in self.vertex_to_point_mapping:
                utils.assert_points_are_close(self.vertex_to_point_mapping[v], Point(line.coords[-1]))
            self.vertex_to_point_mapping[v] = Point(line.coords[-1])

            self.edge_to_line_mapping[edge_key(u, v)] = line

        self.edge_attached_quarry: Dict[FrozenSet[int], int] = dict()
        self.distances_to_quarries: DefaultDict[int, Dict[int, float]] = defaultdict(dict)
        self.second_vertex_in_path: DefaultDict[int, Dict[int, float]] = defaultdict(dict)

        self.original_edge = dict()
        for u, v in self.graph.edges:
            self.original_edge[edge_key(u, v)] = edge_key(u, v)

    def get_available_vertex_id(self):
        """
        Доступный идентификатор для вершины.

        :return:
        """
        self.available_vertex_id += 1

        return self.available_vertex_id

    def compute_distances_to_quarries(self):
        # language=rst
        """
        Вычисление расстояний до карьеров для каждой вершины.

        :return:
        """

        for quarry in self.quarries:
            paths_lengths = nx.shortest_path_length(self.graph, source=quarry, weight="weight")
            paths = nx.shortest_path(self.graph, source=quarry, weight="weight")

            for facility, distance in paths_lengths.items():
                self.distances_to_quarries[facility][quarry] = distance
                self.second_vertex_in_path[facility][quarry] = paths[facility][-2] if len(paths[facility]) > 1 else None

        for facility in self.usual_vertices:
            if not self.distances_to_quarries[facility]:
                raise ValueError("Не для всех объектов существует путь до карьера.")

    def traverse_edges_by_increasing_distance_to_quarry(self) -> List[Tuple[int]]:
        """
        Обход ребер в порядке возрастания расстояния до ближайшего карьера

        :return:
        """

        distances_and_edges = []
        for u, v in self.graph.edges:
            u_min_distance = min(self.distances_to_quarries[u].values())
            v_min_distance = min(self.distances_to_quarries[v].values())
            edge_distance = min(u_min_distance, v_min_distance)

            distances_and_edges.append((edge_distance, (u, v)))

        distances_and_edges.sort()

        return list(map(lambda edge_tuple: edge_tuple[1], distances_and_edges))

    def find_nearest_not_empty_quarry(self, vertex):
        """
        Поиск ближайшего карьера

        :param facility:
        :return:
        """
        min_value = None
        min_key = None
        for key, value in self.distances_to_quarries[vertex].items():
            if not np.isclose(self.quarries_capacities[key], 0) and (min_value is None or value < min_value):
                min_value = value
                min_key = key

        return min_key

    def split_edge(self, start_vertex: int, end_vertex: int, new_edge_length: float, from_end=False) -> Tuple[int, int, int]:
        """
        Разбиение ребра на два. Длина нового ребра должна быть меньше длины текущего. Длина нового ребра отсчитывается от первой точки.

        :param linear:
        :param new_edge_length:
        :return:
        """

        line = self.edge_to_line_mapping[edge_key(start_vertex, end_vertex)]
        if from_end:
            line = LineString(reversed(line.coords))

        length = line.length

        assert new_edge_length < length, "Длина нового ребра при разбиении больше длины текущего."

        split_coeff = new_edge_length / length

        new_point = line.interpolate(split_coeff, normalized=True)
        start_line, end_line = utils.split_line_string_by_point(line, new_point)

        self.graph.remove_edge(start_vertex, end_vertex)
        del self.edge_to_line_mapping[edge_key(start_vertex, end_vertex)]
        del self.first_poit_vertex[edge_key(start_vertex, end_vertex)]
        del self.last_point_vertex[edge_key(start_vertex, end_vertex)]

        new_vertex = self.get_available_vertex_id()

        self.graph.add_node(new_vertex)
        self.usual_vertices.add(new_vertex)
        self.vertex_to_point_mapping[new_vertex] = new_point

        self.graph.add_edge(start_vertex, new_vertex, weight=length * split_coeff)
        self.graph.add_edge(new_vertex, end_vertex, weight=length * (1 - split_coeff))
        self.first_poit_vertex[edge_key(start_vertex, new_vertex)] = start_vertex
        self.first_poit_vertex[edge_key(new_vertex, end_vertex)] = new_vertex
        self.last_point_vertex[edge_key(start_vertex, new_vertex)] = new_vertex
        self.last_point_vertex[edge_key(new_vertex, end_vertex)] = end_vertex
        self.edge_to_line_mapping[edge_key(start_vertex, new_vertex)] = start_line
        self.edge_to_line_mapping[edge_key(new_vertex, end_vertex)] = end_line

        self._recompute_paths(start_vertex, end_vertex, new_vertex)

        self.original_edge[edge_key(start_vertex, new_vertex)] = self.original_edge[edge_key(start_vertex, end_vertex)]
        self.original_edge[edge_key(new_vertex, end_vertex)] = self.original_edge[edge_key(start_vertex, end_vertex)]
        del self.original_edge[edge_key(start_vertex, end_vertex)]

        return start_vertex, new_vertex, end_vertex

    def _recompute_paths(self, start_vertex, end_vertex, new_vertex):
        """
        Пересчет оптимальных путей для вершины, полученной с помощью разбиения ребра

        :param start_vertex:
        :param end_vertex:
        :param new_vertex:
        :return:
        """

        first_new_length = self.graph.get_edge_data(start_vertex, new_vertex)["weight"]
        new_second_length = self.graph.get_edge_data(end_vertex, new_vertex)["weight"]

        self.distances_to_quarries[new_vertex] = dict()
        self.second_vertex_in_path[new_vertex] = dict()

        for quarry, first_distance in self.distances_to_quarries[start_vertex].items():
            second_distance = self.distances_to_quarries[end_vertex][quarry]
            if first_distance + first_new_length < second_distance + new_second_length:
                self.distances_to_quarries[new_vertex][quarry] = first_distance + first_new_length
                self.second_vertex_in_path[new_vertex][quarry] = start_vertex
            else:
                self.distances_to_quarries[new_vertex][quarry] = second_distance + new_second_length
                self.second_vertex_in_path[new_vertex][quarry] = end_vertex

        for quarry, second_vertex_in_path in self.second_vertex_in_path[end_vertex].items():
            if second_vertex_in_path == start_vertex:
                self.second_vertex_in_path[end_vertex][quarry] = new_vertex

        for quarry, second_vertex_in_path in self.second_vertex_in_path[start_vertex].items():
            if second_vertex_in_path == end_vertex:
                self.second_vertex_in_path[start_vertex][quarry] = new_vertex

    @classmethod
    def read_from_file(cls, path: Path):
        """
        Чтение сети из файла.

        :param path:
        :return:
        """
        with open(path) as f:
            n_of_vertices = int(f.readline())
            n_of_quarries = int(f.readline())
            n_of_edges = int(f.readline())

            vertices = list(map(int, f.readline().split()))

            quarries_capacities = dict()
            for _ in range(n_of_quarries):
                vertex, capacity = f.readline().split()
                vertex = int(vertex)
                capacity = float(capacity)
                quarries_capacities[vertex] = capacity

            incidence_list = []
            for _ in range(n_of_edges):
                u, v, wkt_line = f.readline().split(maxsplit=2)
                u, v, line = int(u), int(v), wkt.loads(wkt_line)

                incidence_list.append((u, v, line))

        return cls(vertices, quarries_capacities, incidence_list)
