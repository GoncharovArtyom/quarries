"""
Модуль, отвечающий за отрисовку дорожной сети.
"""

from matplotlib import pyplot as plt
from network import Network


def draw_raw_road_network(road_network: Network):
    """
    Отрисовка дорожной сети до вычисления ближайших карьеров.

    :param road_network:
    :return:
    """

    quarries_color = "y"
    other_color = "black"

    for vertex in road_network.usual_vertices:
        point = road_network.vertex_to_point_mapping[vertex]

        plt.plot(point.x, point.y, "o", color=other_color)

    for vertex in road_network.quarries:
        point = road_network.vertex_to_point_mapping[vertex]

        plt.annotate(
            f"Объем: {road_network.quarries_capacities[vertex]}",
            xy=(point.x, point.y), xytext=(-20, 20),
            textcoords='offset points', ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        plt.plot(point.x, point.y, "o", color=quarries_color)

    for line in road_network.edge_to_line_mapping.values():
        plt.plot(line.coords.xy[0], line.coords.xy[1], color=other_color, zorder=1)

    plt.show()


def draw_calculated_road_network(road_network: Network):
    """
    Отрисовка дорожной сети до вычисления ближайших карьеров.

    :param road_network:
    :return:
    """

    ordered_quarries = list(road_network.quarries)
    quarry_to_ind_mapping = {quarry: ind for ind, quarry in enumerate(ordered_quarries)}

    quarries_color_map = plt.cm.get_cmap("plasma", len(ordered_quarries))
    other_color = "black"

    for vertex in road_network.usual_vertices:
        point = road_network.vertex_to_point_mapping[vertex]

        plt.plot(point.x, point.y, "o", color=other_color)

    for ind, vertex in enumerate(road_network.quarries):
        point = road_network.vertex_to_point_mapping[vertex]

        plt.annotate(
            f"Объем: {road_network.quarries_capacities[vertex]}",
            xy=(point.x, point.y), xytext=(-20, 20),
            textcoords='offset points', ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        plt.plot(point.x, point.y, "o", color=quarries_color_map(quarry_to_ind_mapping[vertex]))

    for (u, v), line in road_network.edge_to_line_mapping.items():
        attached_quarry = road_network.edge_attached_quarry[Network.edge_key(u, v)]
        plt.plot(line.coords.xy[0], line.coords.xy[1], zorder=1, color=quarries_color_map(quarry_to_ind_mapping[attached_quarry]))

    plt.show()
