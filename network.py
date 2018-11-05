"""
Класс, объединяющий в себе логику работы с графом.
"""

import networkx as nx
import numpy as np
import shapely.wkt as wkt
from shapely.geometry import Point, LineString
from typing import List, Set, Dict, Tuple, FrozenSet
from pathlib import Path


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
        self.available_id = max(vertices) + 1

        self.first_poit_vertex = dict()
        self.last_point_vertex = dict()
        self.vertex_to_point_mapping = dict()
        self.edge_to_line_mapping = dict()
        for u, v, line in incidence_list:
            self.graph.add_edge(u, v)
            self.first_poit_vertex[self.edge_key(u, v)] = u
            self.last_point_vertex[self.edge_key(u, v)] = v

            if u in self.vertex_to_point_mapping:
                self.assert_points_are_close(self.vertex_to_point_mapping[u], Point(line.coords[0]))
            self.vertex_to_point_mapping[u] = Point(line.coords[0])

            if v in self.vertex_to_point_mapping:
                self.assert_points_are_close(self.vertex_to_point_mapping[v], Point(line.coords[-1]))
            self.vertex_to_point_mapping[v] = Point(line.coords[-1])

            self.edge_to_line_mapping[self.edge_key(u, v)] = line

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
                vertex, capacity = map(int, f.readline().split())
                quarries_capacities[vertex] = capacity

            incidence_list = []
            for _ in range(n_of_edges):
                u, v, wkt_line = f.readline().split(maxsplit=2)
                u, v, line = int(u), int(v), wkt.loads(wkt_line)

                incidence_list.append((u, v, line))

        return cls(vertices, quarries_capacities, incidence_list)

    @staticmethod
    def assert_points_are_close(p1: Point, p2: Point):
        """
        Проверка, что точки расположены близко.

        :param p1:
        :param p2:
        :return:
        """

        assert np.isclose(p1.distance(p2), 0), "Точки не совпадают."

    @staticmethod
    def edge_key(u: int, v: int) -> FrozenSet[int]:
        """
        Значение, которое может быть использовано в качестве ключа для ребра. Порядок вершин не важен.

        :param u:
        :param v:
        :return:
        """

        return frozenset((u, v))
