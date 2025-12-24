'''Utilities to build an emoji co-occurrence graph from review data.'''
from itertools import combinations
from collections import Counter

import pandas as pd
import networkx as nx


class GraphBuilder:
    '''
    Build an emoji co-occurrence graph from a reviews DataFrame.

    The input DataFrame is expected to have an 'emojis' column where
    each cell is either NaN or a whitespace-separated string of emoji
    tokens (e.g., ":smile: :thumbs_up:").

    Attributes:
        reviews (pandas.DataFrame): Input DataFrame with an 'emojis' column.
        graph (networkx.Graph): The resulting emoji graph.
    '''
    def __init__(self, reviews: pd.DataFrame):
        '''
        Args:
            reviews: A pandas DataFrame containing an 'emojis' column.
        '''
        self.reviews = reviews
        self.graph = nx.Graph()

    def parse_emojis(self, x: str) -> list[str]:
        '''
        Parse a whitespace-separated emoji string into a list.
        Handles missing values (NaN) by returning an empty list.

        Args:
            x: A string of emojis separated by whitespace, or NaN.

        Returns:
            A list of individual emoji tokens (str). Example: [":+1:", ":ok:"]
        '''
        if pd.isna(x):
            return []
        return [e.strip() for e in x.split()]

    def create_nodes(self) -> Counter:
        '''
        Create emoji lists and count co-occurrence pairs across reviews.

        - Adds a new column `emoji_list` to `self.reviews` containing parsed
          emoji lists (via `parse_emojis`).
        - Counts unordered emoji co-occurrence pairs per review (unique set).
        - Returns a Counter mapping (emoji1, emoji2) -> co-occurrence count.

        Returns:
            collections.Counter where keys are 2-tuples of emoji strings
            (emoji_a, emoji_b) and values are integer counts.
        '''
        self.reviews["emoji_list"] = self.reviews["emojis"].apply(
            self.parse_emojis
        )
        edge_counter = Counter()

        for emojis in self.reviews["emoji_list"]:
            if len(emojis) < 2:
                continue

            for e1, e2 in combinations(sorted(set(emojis)), 2):
                edge_counter[(e1, e2)] += 1

        return edge_counter

    def build_graph(self) -> nx.Graph:
        '''
        Build and return a NetworkX graph of emoji co-occurrences.

        - Uses `create_nodes` to compute pairwise co-occurrence counts.
        - Adds edges with attribute `weight` for co-occurrence counts.
        - Computes emoji frequency across all reviews and sets a node
          attribute `frequency` for each node.

        Returns:
            A `networkx.Graph` with nodes representing emojis and edges
            labeled by `weight`; node attribute `frequency` stores counts.
        '''
        edge_counter = self.create_nodes()

        for (e1, e2), weight in edge_counter.items():
            self.graph.add_edge(e1, e2, weight=weight)

        emoji_freq = Counter(
            e for emojis in self.reviews["emoji_list"] for e in emojis
        )

        nx.set_node_attributes(self.graph, emoji_freq, name="frequency")
        return self.graph
