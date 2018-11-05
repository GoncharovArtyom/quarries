import painter

from network import Network
from pathlib import Path
from edges_splitter import EdgesSplitter

path = Path('input.txt')
network = Network.read_from_file(path)
splitter = EdgesSplitter(network)
splitter.calculate()

painter.draw_raw_road_network(splitter.old_road_network)
painter.draw_calculated_road_network(splitter.road_network)