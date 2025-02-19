import os
import time
from concurrent import futures
import httpx

import h5py
from qdrant_client import QdrantClient

from benchmark.config import DATA_DIR


class BenchmarkSearch:

    def __init__(self, collection_name="benchmark_collection"):
        self.collection_name = collection_name
        vectors_path = os.path.join(DATA_DIR, 'glove-100-angular.hdf5')
        self.data = h5py.File(vectors_path)
        self.client = QdrantClient(limits=httpx.Limits(max_connections=None, max_keepalive_connections=0))
        self.vector_size = len(self.data['test'][0])

    def search_one(self, i):
        top = 10
        true_result = set(self.data['neighbors'][i][:top])
        start = time.time()
        res = self.client.search(
            self.collection_name,
            query_vector=self.data['test'][i],
            top=top,
            append_payload=False
        )
        end = time.time()
        search_res = set(x.id for x in res)
        precision = len(search_res.intersection(true_result)) / top
        return precision, end - start

    def search_all(self, parallel_queries=4):
        num_queries = len(self.data['test'])
        print(f"Search with {parallel_queries} threads")
        start = time.time()

        future_results = []
        if parallel_queries == 1:
            for i in range(num_queries):
                res = self.search_one(i)
                future_results.append(res)
        else:
            with futures.ThreadPoolExecutor(max_workers=parallel_queries) as executor:
                future_results = executor.map(
                    self.search_one,
                    range(num_queries)
                )

        precisions, latencies = list(zip(*future_results))
        end = time.time()

        
        print(f"avg precision = {sum(precisions) / len(precisions):.3f}")
        print(f"total time = {end - start:.3f} sec")
        print(f"time per query = {(end - start) / num_queries:.4f} sec")
        print(f"query latency = {sum(latencies) / len(latencies):.4f} sec")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--parallel", default=4, type=int, help="number of threads for requests")

    args = parser.parse_args()

    benchmark = BenchmarkSearch()
    benchmark.search_all(parallel_queries=args.parallel)

