"""
Полезные функции.
"""

import numpy as np
from shapely.geometry import LineString, Point

import configs


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

    from network import Network

    total_cost = 0
    for (u, v), line in road_network.edge_to_line_mapping.items():
        attached_quarry = road_network.edge_attached_quarry[Network.edge_key(u, v)]
        distance_to_quarry = min(road_network.distances_to_quarries[u][attached_quarry], road_network.distances_to_quarries[v][attached_quarry])

        total_cost += compute_line_cost(line, distance_to_quarry)

    return total_cost


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
