from pathlib import Path

import painter
import utils
from edges_splitter import EdgesSplitter
from grid import Grid
from network import Network
import numpy as np

# path = Path('example1.txt')
# network = Network.read_from_file(path)
# splitter = EdgesSplitter(network)
# splitter.calculate()
#
# painter.draw_raw_road_network(splitter.old_road_network)
# painter.draw_calculated_road_network(splitter.road_network)
#
# cost = utils.compute_road_network_cost(splitter.road_network)
#
# print(f"Стоимость строительства дорожной сети: {cost}")
from network_builder import NetworkBuilder
#
t, q = utils.read_terminal_points("input_terminal_points")
p = np.vstack((t, q))

g = Grid(p, set(range(len(t), len(p))))
g.generate()
# painter.draw_grid(g)
#
# print(g.distance_matrix[0, 1])

nb = NetworkBuilder(g)
network = nb.build_network()

splitter = EdgesSplitter(network)
splitter.calculate()

painter.draw_raw_road_network(splitter.old_road_network)
painter.draw_calculated_road_network(splitter.road_network)
#
cost = utils.compute_road_network_cost(splitter.road_network)

print(f"Стоимость строительства дорожной сети: {cost}")
