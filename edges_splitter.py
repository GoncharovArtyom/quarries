#!/usr/bin/env python
# coding: utf-8

"""Класс, отвечающий за разбиение ребер дорожной сети в зависимости от расположения карьеров."""

import networkx as nx
import numpy as np

from collections import defaultdict
from shapely.geometry import Point, LineString
from typing import Set, Dict, DefaultDict, Tuple, List
from uuid import UUID, uuid4

from configs import context_params
from ontology import logger
from ontology.facility import Facility
from ontology.linear import Linear
from ontology.network import Network
from ontology.classifier import Classifier


class EdgesSplitter:
    """
    Класс, отвечающий за разбиение ребер дорожной сети в зависимости от расположения карьеров.
    """

    def __init__(self, road_network: Network, quarries_classes_to_use: Set[UUID]):
        self.classifier: Classifier = context_params.wellfield.classifier

        if road_network.metaclass_id not in self.classifier.get_all_roads_metaclass_ids():
            message = "Задача с карьерами может быть посчитана только для сети дорог."
            logger.error(message)
            raise AssertionError(message)

        quarries = {facility for facility in road_network.facilities if facility.class_id in quarries_classes_to_use}
        not_quarry_facilities = {facility for facility in road_network.facilities if facility.class_id not in quarries_classes_to_use}
        if not quarries:
            message = "Сеть дорог должна содержать заданные карьеры."
            logger.error(message)
            raise AssertionError(message)

        self.road_network = road_network

        self.quarries: Set[Facility] = quarries
        self.not_quarry_facilities = not_quarry_facilities
        self.quarries_capacities = {quarry: quarry.props["capacity"] for quarry in self.quarries}
        self.edge_attached_quarry = dict()

        self.distances_to_quarries: DefaultDict[Facility, Dict[Facility, float]] = defaultdict(dict)
        self.second_vertex_in_path: DefaultDict[Facility, Dict[Facility, float]] = defaultdict(dict)

    def calculate(self):
        # language=rst
        """
        Расчет карьеров

        :return:
        """

        self._compute_distances_to_quarries()

        for linear in self._traverse_linears_by_increasing_distance_to_quarry():
            self._construct_edge(linear)

    def _compute_distances_to_quarries(self):
        # language=rst
        """
        Вычисление расстояний до карьеров для каждой вершины.

        :return:
        """

        for quarry in self.quarries:
            paths_lengths = nx.shortest_path_length(self.road_network.graph, source=quarry, weight="weight")
            paths = nx.shortest_path(self.road_network.graph, source=quarry, weight="weight")

            for facility, distance in paths_lengths.items():
                self.distances_to_quarries[facility][quarry] = distance
                self.second_vertex_in_path[facility][quarry] = paths[facility][-2] if len(paths[facility]) > 1 else None

        for facility in self.not_quarry_facilities:
            if not self.distances_to_quarries[facility]:
                message = "Не для всех объектов существует путь до карьера."
                logger.error(message)
                raise AssertionError(message)

    def _traverse_linears_by_increasing_distance_to_quarry(self) -> List[Linear]:
        # language=rst
        """
        Обход ребер в порядке возрастания расстояния до ближайшего карьера

        :return:
        """

        linears = []
        for linear in self.road_network.linears:
            u = linear.first_point_facility
            v = linear.last_point_facility
            u_min_distance = min(self.distances_to_quarries[u].values())
            v_min_distance = min(self.distances_to_quarries[v].values())
            edge_distance = min(u_min_distance, v_min_distance)

            linears.append((edge_distance, linear))

        linears.sort()

        return list(map(lambda edge_tuple: edge_tuple[1], linears))

    def _recompute_paths(self, start_facility, end_facility, new_facility):
        # language=rst
        """
        Пересчет оптимальных путей для вершины, полученной с помощью разбиения ребра

        :param start_facility:
        :param end_facility:
        :param new_facility:
        :return:
        """

        first_new_length = self.road_network.graph.get_edge_data(start_facility, new_facility)["weight"]
        new_second_length = self.road_network.graph.get_edge_data(end_facility, new_facility)["weight"]

        self.road_network.graph.node[new_facility]["distances_to_quarries"] = dict()
        self.road_network.graph.node[new_facility]["second_vertex_in_path_to"] = dict()

        for quarry, first_distance in self.distances_to_quarries[start_facility].items():
            second_distance = self.distances_to_quarries[end_facility][quarry]
            if first_distance + first_new_length < second_distance + new_second_length:
                self.distances_to_quarries[new_facility][quarry] = first_distance + first_new_length
                self.second_vertex_in_path[new_facility][quarry] = start_facility
            else:
                self.distances_to_quarries[new_facility][quarry] = second_distance + new_second_length
                self.second_vertex_in_path[new_facility][quarry] = end_facility

        for quarry, second_vertex_in_path in self.second_vertex_in_path[end_facility].items():
            if second_vertex_in_path == start_facility:
                self.second_vertex_in_path[end_facility][quarry] = new_facility

        for quarry, second_vertex_in_path in self.second_vertex_in_path[start_facility].items():
            if second_vertex_in_path == end_facility:
                self.second_vertex_in_path[start_facility][quarry] = new_facility

    def _split_edge(self, linear: Linear, new_edge_length: float, from_end=False) -> Tuple[Linear, Linear]:
        # language=rst
        """
        Разбиение ребра на два. Длина нового ребра должна быть меньше длины текущего. Длина нового ребра отсчитывается от первой точки.

        :param linear:
        :param new_edge_length:
        :return:
        """

        length = linear.geom.length
        start_facility = linear.first_point_facility
        end_facility = linear.last_point_facility

        if length <= new_edge_length:
            message = "Длина нового ребра при разбиении больше длины текущего."
            logger.error(message)
            raise AssertionError(message)

        split_coeff = new_edge_length / length
        if from_end:
            split_coeff = 1 - split_coeff

        line = linear.geom
        new_point = line.interpolate(split_coeff, normalized=True)
        start_line, end_line = self._split_line_string_by_point(line, new_point)

        new_facility = Facility(data=dict(
            class_id=self.classifier.get_nodal_facility_class_id(),
            name="Узловой объект",
            active=False,
            exit_point=new_point
        ))

        start_linear = Linear.from_other(linear,
                                         geom=start_line,
                                         first_point_facility=start_facility,
                                         last_point_facility=new_facility)

        end_linear = Linear.from_other(linear,
                                       geom=end_line,
                                       first_point_facility=new_facility,
                                       last_point_facility=end_facility)

        self.road_network.delete_linear(linear)
        self.road_network.add_linear(start_linear)
        self.road_network.add_linear(end_linear)

        self._recompute_paths(start_facility, end_facility, new_facility)

        return start_linear, end_linear

    def _find_nearest_not_empty_quarry(self, facility):
        # language=rst
        """
        Поиск ближайшего карьера

        :param facility:
        :return:
        """
        min_value = None
        min_key = None
        for key, value in self.distances_to_quarries[facility].items():
            if not np.isclose(self.quarries_capacities[key], 0) and (min_value is None or value < min_value):
                min_value = value
                min_key = key

        return min_key

    def _construct_edge(self, linear: Linear):
        # language=rst
        """
        Строительство ребра

        :param linear:
        :return:
        """

        start_facility = linear.first_point_facility
        end_facility = linear.last_point_facility
        start_nearest_quarry = self._find_nearest_not_empty_quarry(start_facility)
        end_nearest_quarry = self._find_nearest_not_empty_quarry(end_facility)

        # Для одной из вершин все доступные карьеры опустошены
        if start_nearest_quarry is None or end_nearest_quarry is None:
            return

        # Вершина start всегда ближайшая к карьеру
        were_facilities_inverted = False
        if self.distances_to_quarries[start_facility][start_nearest_quarry] > self.distances_to_quarries[end_facility][end_nearest_quarry]:
            start_facility, end_facility = end_facility, start_facility
            start_nearest_quarry, end_nearest_quarry = end_nearest_quarry, start_nearest_quarry
            were_facilities_inverted = True

        # Если расстояния от дальнего конца ребра до ближайшего карьера ближнего конца почти совпадает с растоянием от
        # дальнего конца ребра до его собственного ближайшего карьера, то выбираем ближайший карьер ближнего конца.
        if np.isclose(self.distances_to_quarries[end_facility][start_nearest_quarry],
                      self.distances_to_quarries[end_facility][end_nearest_quarry]):
            end_nearest_quarry = start_nearest_quarry

        length = linear.geom.length

        # Если ближайшие карьеры двух концов ребер не совпали, или совпали, но пути, ведущие к карьеру отличаются,
        # то необходимо разбить ребро на части
        if start_nearest_quarry != end_nearest_quarry or \
                not np.isclose(self.distances_to_quarries[end_facility][end_nearest_quarry], self.distances_to_quarries[start_facility][start_nearest_quarry] + length):

            path_difference = self.distances_to_quarries[end_facility][end_nearest_quarry] - self.distances_to_quarries[start_facility][start_nearest_quarry]
            new_length = (length + path_difference) / 2
            start_linear, end_linear = self._split_edge(linear, new_length, from_end=were_facilities_inverted)

            self._construct_edge(start_linear)
            self._construct_edge(end_linear)

        else:
            nearest_quarry = start_nearest_quarry
            required_volume = self._compute_required_volume(linear)

            if required_volume < self.quarries_capacities[nearest_quarry]:
                self.quarries_capacities[nearest_quarry] -= required_volume
                self.edge_attached_quarry[linear] = nearest_quarry
            else:
                new_edge_length = self._find_max_road_length(linear, self.quarries_capacities[nearest_quarry])
                start_linear, end_linear = self._split_edge(linear, new_edge_length, from_end=were_facilities_inverted)

                self.quarries_capacities[nearest_quarry] = 0
                if not were_facilities_inverted:
                    self.edge_attached_quarry[start_linear] = nearest_quarry
                    self._construct_edge(end_linear)
                else:
                    self.edge_attached_quarry[end_linear] = nearest_quarry
                    self._construct_edge(start_linear)

    @classmethod
    def _split_line_string_by_point(cls, line_string, point):
        # language=rst
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

    @staticmethod
    def _compute_required_volume(linear: Linear):
        # language=rst
        """
        Вычисление объема, необходимого для строительства дороги

        :param linear:
        :return:
        """
        length = linear.geom.length
        coeff = linear.props["road_height"] * linear.props["road_width"]

        return coeff * length

    @staticmethod
    def _find_max_road_length(linear: Linear, capacity: float):
        # language=rst
        """
        Вычисление максимальной длины дороги, которая может быть постоенна из заданного объема материалов

        :param linear:
        :param capacity:
        :return:
        """
        coeff = linear.props["road_height"] * linear.props["road_width"]

        return capacity / coeff
