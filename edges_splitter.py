#!/usr/bin/env python
# coding: utf-8

"""Класс, отвечающий за разбиение ребер дорожной сети в зависимости от расположения карьеров."""

from copy import deepcopy

import numpy as np

import utils
from network import Network


class EdgesSplitter:
    """
    Класс, отвечающий за разбиение ребер дорожной сети в зависимости от расположения карьеров.
    """

    def __init__(self, road_network: Network):

        self.road_network = road_network
        self.old_road_network = deepcopy(road_network)

    def calculate(self):
        # language=rst
        """
        Расчет карьеров

        :return:
        """

        self.road_network.compute_distances_to_quarries()

        for u, v in self.road_network.traverse_edges_by_increasing_distance_to_quarry():
            self._construct_edge(u, v)

    def _construct_edge(self, u: int, v: int):
        """
        Строительство ребра

        :param linear:
        :return:
        """

        start_vertex = self.road_network.first_poit_vertex[Network.edge_key(u, v)]
        end_vertex = self.road_network.last_point_vertex[Network.edge_key(u, v)]

        start_nearest_quarry = self.road_network.find_nearest_not_empty_quarry(start_vertex)
        end_nearest_quarry = self.road_network.find_nearest_not_empty_quarry(end_vertex)

        # Для одной из вершин все доступные карьеры опустошены
        if start_nearest_quarry is None or end_nearest_quarry is None:
            raise ValueError("Объема заданных карьеров недостаточно, чтобы построить требуемую дорожную сеть.")

        # Вершина start всегда ближайшая к карьеру
        were_vertices_inverted = False
        if (self.road_network.distances_to_quarries[start_vertex][start_nearest_quarry] >
                self.road_network.distances_to_quarries[end_vertex][end_nearest_quarry]):
            start_vertex, end_vertex = end_vertex, start_vertex
            start_nearest_quarry, end_nearest_quarry = end_nearest_quarry, start_nearest_quarry
            were_vertices_inverted = True

        # Если расстояния от дальнего конца ребра до ближайшего карьера ближнего конца почти совпадает с растоянием от
        # дальнего конца ребра до его собственного ближайшего карьера, то выбираем ближайший карьер ближнего конца.
        if np.isclose(self.road_network.distances_to_quarries[end_vertex][start_nearest_quarry],
                      self.road_network.distances_to_quarries[end_vertex][end_nearest_quarry]):
            end_nearest_quarry = start_nearest_quarry

        length = self.road_network.edge_to_line_mapping[Network.edge_key(start_vertex, end_vertex)].length

        # Если ближайшие карьеры двух концов ребер не совпали, или совпали, но пути, ведущие к карьеру отличаются,
        # то необходимо разбить ребро на части
        if start_nearest_quarry != end_nearest_quarry or \
                not np.isclose(self.road_network.distances_to_quarries[end_vertex][end_nearest_quarry],
                               self.road_network.distances_to_quarries[start_vertex][start_nearest_quarry] + length):

            path_difference = (self.road_network.distances_to_quarries[end_vertex][end_nearest_quarry] -
                               self.road_network.distances_to_quarries[start_vertex][start_nearest_quarry])
            new_length = (length + path_difference) / 2

            start_vertex, new_vertex, end_vertex = self.road_network.split_edge(start_vertex, end_vertex, new_length, from_end=were_vertices_inverted)

            self._construct_edge(start_vertex, new_vertex)
            self._construct_edge(new_vertex, end_vertex)

        else:
            line = self.road_network.edge_to_line_mapping[Network.edge_key(start_vertex, end_vertex)]
            nearest_quarry = start_nearest_quarry
            required_volume = utils.compute_required_volume(line)

            if (required_volume < self.road_network.quarries_capacities[nearest_quarry] or
                    np.isclose(required_volume, self.road_network.quarries_capacities[nearest_quarry])):
                self.road_network.quarries_capacities[nearest_quarry] -= required_volume
                self.road_network.edge_attached_quarry[Network.edge_key(start_vertex, end_vertex)] = nearest_quarry
            else:
                new_edge_length = utils.find_max_road_length(self.road_network.quarries_capacities[nearest_quarry])
                start_vertex, new_vertex, end_vertex = self.road_network.split_edge(start_vertex, end_vertex, new_edge_length, from_end=were_vertices_inverted)

                self.road_network.quarries_capacities[nearest_quarry] = 0
                if not were_vertices_inverted:
                    self.road_network.edge_attached_quarry[Network.edge_key(start_vertex, new_vertex)] = nearest_quarry
                    self._construct_edge(new_vertex, end_vertex)
                else:
                    self.road_network.edge_attached_quarry[Network.edge_key(new_vertex, end_vertex)] = nearest_quarry
                    self._construct_edge(start_vertex, new_vertex)
