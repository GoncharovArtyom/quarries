"""
Полезные функции.
"""
from collections import defaultdict
from pathlib import Path
from typing import FrozenSet

import numpy as np
from shapely.geometry import LineString, Point

import configs
import networkx as nx


def split_line_string_by_point(line_string: LineString, point: Point):
    """
    Разбиение LineString на две части по проекции точки

    :param line_string:
    :param point:
    :return:
    """

    distance = line_string.project(point)

    if distance <= 0.0 or distance >= line_string.length:
        return [LineString(line_string)]

    coords = list(line_string.coords)
    for i, p in enumerate(coords):
        pd = line_string.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i + 1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line_string.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]


def compute_required_volume(line: LineString):
    """
    Вычисление объема, необходимого для строительства дороги

    :param linear:
    :return:
    """
    length = line.length
    coeff = configs.ROAD_HEIGHT * configs.ROAD_WIDTH

    return coeff * length


def find_max_road_length(capacity: float):
    """
    Вычисление максимальной длины дороги, которая может быть постоенна из заданного объема материалов

    :param linear:
    :param capacity:
    :return:
    """

    coeff = configs.ROAD_WIDTH * configs.ROAD_HEIGHT

    return capacity / coeff


def assert_points_are_close(p1: Point, p2: Point):
    """
    Проверка, что точки расположены близко.

    :param p1:
    :param p2:
    :return:
    """

    assert np.isclose(p1.distance(p2), 0), "Точки не совпадают."


def compute_road_network_cost(road_network: "Network"):
    """
    Подсчет стоимости дорожной сети.

    :param road_network:
    :return:
    """

    total_cost = 0
    for (u, v), line in road_network.edge_to_line_mapping.items():
        attached_quarry = road_network.edge_attached_quarry[edge_key(u, v)]
        distance_to_quarry = min(road_network.distances_to_quarries[u][attached_quarry], road_network.distances_to_quarries[v][attached_quarry])

        total_cost += compute_line_cost(line, distance_to_quarry)

    return total_cost


def assign_quarries_costs(road_network: "Network", original_graph: nx.Graph):
    """
    Подсчет стоимости дорожной сети.

    :param road_network:
    :return:
    """
    quarries_costs = defaultdict(lambda: 0)
    for (u, v), line in road_network.edge_to_line_mapping.items():
        attached_quarry = road_network.edge_attached_quarry[edge_key(u, v)]
        distance_to_quarry = min(road_network.distances_to_quarries[u][attached_quarry], road_network.distances_to_quarries[v][attached_quarry])

        quarries_costs[road_network.original_edge[edge_key(u, v)]] += compute_line_cost(line, distance_to_quarry)

    nx.set_edge_attributes(original_graph, quarries_costs, name="quarry_cost")


def compute_line_cost(line: LineString, distance_to_quarry: float):
    """
    Подсчет стоимости одного ребра.

    :param line:
    :param distance_to_quarry:
    :return:
    """
    length = line.length

    coeff = configs.ROAD_HEIGHT * configs.ROAD_WIDTH * configs.UNIT_COST
    value = length * distance_to_quarry + length ** 2 / 2

    return coeff * value


def read_terminal_points(path_to_file: Path):
    """
    Чтение точек из файла.

    :param path_to_file:
    :return:
    """
    terminal_points = []
    quarries = []
    with open(path_to_file) as f:
        n_terminal_points = int(f.readline())
        for _ in range(n_terminal_points):
            x, y = map(float, f.readline().split())
            terminal_points.append((x, y))

        n_quarries = int(f.readline())
        for _ in range(n_quarries):
            x, y = map(float, f.readline().split())
            quarries.append((x, y))

    return np.array(terminal_points), np.array(quarries)



def edge_key(u: int, v: int) -> FrozenSet[int]:
    """
    Значение, которое может быть использовано в качестве ключа для ребра. Порядок вершин не важен.

    :param u:
    :param v:
    :return:
    """

    return frozenset((u, v))
