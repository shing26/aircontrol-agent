# src/vision/dtw_recognizer.py
import numpy as np

from src.config import EngineConfig


class DTWRecognizer:
    def __init__(self):
        self.templates = {}

    def normalize_sequence(self, seq):
        if len(seq) < 5:
            return None
        arr = np.array(seq, dtype=np.float32)

        # 1. ?????????? (0,0)
        shifted = arr - arr[0]

        # 2. ??????????? 0.0~1.0
        min_xy = np.min(shifted, axis=0)
        max_xy = np.max(shifted, axis=0)
        box_dim = max_xy - min_xy
        max_span = np.max(box_dim)

        if max_span > 1e-5:
            normalized = shifted / max_span
        else:
            normalized = shifted
        return normalized

    def compute_dtw(self, seq1, seq2):
        n, m = len(seq1), len(seq2)
        cost = np.zeros((n, m), dtype=np.float32)
        for i in range(n):
            for j in range(m):
                cost[i, j] = np.linalg.norm(seq1[i] - seq2[j])

        accum_cost = np.zeros((n, m), dtype=np.float32)
        accum_cost[0, 0] = cost[0, 0]

        for i in range(1, n):
            accum_cost[i, 0] = accum_cost[i - 1, 0] + cost[i, 0]
        for j in range(1, m):
            accum_cost[0, j] = accum_cost[0, j - 1] + cost[0, j]

        for i in range(1, n):
            for j in range(1, m):
                accum_cost[i, j] = cost[i, j] + min(
                    accum_cost[i - 1, j],
                    accum_cost[i, j - 1],
                    accum_cost[i - 1, j - 1],
                )

        return accum_cost[-1, -1] / (n + m)

    def register_template(self, name, raw_seq):
        norm_seq = self.normalize_sequence(raw_seq)
        if norm_seq is not None:
            self.templates[name] = norm_seq
            print(
                f"[DTW] Gesture macro registered: {name} "
                f"(length: {len(norm_seq)} frames)"
            )

    def match(self, current_raw_seq):
        norm_current = self.normalize_sequence(current_raw_seq)
        if norm_current is None or not self.templates:
            return None

        best_match = None
        min_dist = float("inf")

        for name, template in self.templates.items():
            dist = self.compute_dtw(norm_current, template)
            if dist < min_dist:
                min_dist = dist
                best_match = name

        if min_dist < EngineConfig.DTW_THRESHOLD:
            return best_match
        return None
