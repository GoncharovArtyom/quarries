from pathlib import Path

import painter
import utils
from edges_splitter import EdgesSplitter
from network import Network

path = Path('input.txt')
network = Network.read_from_file(path)
splitter = EdgesSplitter(network)
splitter.calculate()

painter.draw_raw_road_network(splitter.old_road_network)
painter.draw_calculated_road_network(splitter.road_network)

cost = utils.compute_road_network_cost(splitter.road_network)

print(f"Стоимость строительства дорожной сети: {cost}")
