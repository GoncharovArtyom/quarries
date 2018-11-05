"""
Полезные функции.
"""

import configs
import numpy as np
from shapely.geometry import LineString, Point


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


def find_max_road_length(line: LineString, capacity: float):
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