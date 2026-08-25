#!/usr/bin/env python3
"""
Threshold calibration study for FacePass FabLab (RQ1 / §22 Research Area 1).

Computes genuine vs impostor cosine-similarity distributions from every
enrolled user's stored embeddings and recommends a match threshold for
target False Accept Rates.

Genuine pair   : two different embeddings of the SAME user
Impostor pair  : embeddings from two DIFFERENT users

Usage:
    python -m scripts.calibrate_threshold                 # analyze DB
    python -m scripts.calibrate_threshold --targets 0.01 0.001
"""

import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


def load_embeddings() -> dict:
    """Load {user_id: [emb, ...]} for all active enrolled users."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, face_embedding, face_embedding_2, face_embedding_3
        FROM users WHERE active = 1
    ''')
    rows = cursor.fetchall()
    conn.close()

    store = {}
    for row in rows:
        embs = []
        for i in range(1, 4):
            blob = row[i]
            if blob is not None:
                emb = np.frombuffer(blob, dtype=np.float64)
                norm = np.linalg.norm(emb)
                if norm > 0 and emb.size == 512:
                    embs.append(emb / norm)
        if len(embs) >= 2:
            store[row['user_id']] = embs
    return store


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.clip(np.dot(a, b), -1.0, 1.0))


def collect_scores(store: dict):
    genuine, impostor = [], []
    for uid, embs in store.items():
        for a, b in itertools.combinations(embs, 2):
            genuine.append(similarity(a, b))

    for ua, ub in itertools.combinations(store.keys(), 2):
        for a in store[ua]:
            for b in store[ub]:
                impostor.append(similarity(a, b))
    return np.array(genuine), np.array(impostor)


def far_at_threshold(impostor: np.ndarray, t: float) -> float:
    if impostor.size == 0:
        return 0.0
    return float(np.mean(impostor >= t))


def frr_at_threshold(genuine: np.ndarray, t: float) -> float:
    if genuine.size == 0:
        return 0.0
    return float(np.mean(genuine < t))


def recommend(genuine: np.ndarray, impostor: np.ndarray, targets) -> list:
    """Smallest threshold meeting each FAR target while reporting FRR cost.

    FAR(t) is non-increasing in t, so the feasible set is an upper
    interval: scan ascending and take the FIRST feasible threshold
    (lowest FRR among thresholds satisfying the FAR bound).
    """
    out = []
    grid = np.linspace(0.05, 0.95, 181)
    for far_target in targets:
        chosen = None
        for t in grid:
            if far_at_threshold(impostor, t) <= far_target:
                chosen = t
                break
        if chosen is None:
            out.append((far_target, None, None))
        else:
            out.append((far_target, round(float(chosen), 3),
                        round(frr_at_threshold(genuine, chosen), 4)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description='RQ1 threshold calibration')
    parser.add_argument('--targets', type=float, nargs='*', default=[0.01, 0.001],
                        help='FAR targets, e.g. --targets 0.01 0.001')
    args = parser.parse_args()

    store = load_embeddings()
    n_users = len(store)
    print('=' * 60)
    print('FacePass FabLab - Threshold Calibration (RQ1)')
    print('=' * 60)

    if n_users < 2:
        print(f'\nNeed >= 2 users with >= 2 stored embeddings each '
              f'(found {n_users}).')
        print('Enroll more members first: Members page or enrollment CLI.')
        return 1

    genuine, impostor = collect_scores(store)

    def stats(name, arr):
        if arr.size == 0:
            print(f'  {name:<9}: no pairs')
            return
        print(f'  {name:<9}: n={arr.size:<5} mean={arr.mean():.3f} '
              f'min={arr.min():.3f} max={arr.max():.3f}')

    print('\nScore distributions:')
    stats('genuine', genuine)
    stats('impostor', impostor)

    sep = ''
    if genuine.size and impostor.size:
        gap = genuine.mean() - impostor.mean()
        sep = f'\nSeparation (genuine mean - impostor mean): {gap:.3f}'
        print(sep)
        if gap < 0.15:
            print('WARNING: weak separation — re-enroll with better lighting/poses.')

    print('\nRecommended thresholds:')
    print('  FAR target | threshold | FRR cost')
    for far_t, thr, frr in recommend(genuine, impostor, args.targets):
        if thr is None:
            print(f'  {far_t:>9}  |  unreachable with current data')
        else:
            print(f'  {far_t:>9}  |    {thr:.3f}  |  {frr:.2%}')

    d_prime = 0.0
    if genuine.size > 1 and impostor.size > 1:
        pooled = np.sqrt((genuine.std() ** 2 + impostor.std() ** 2) / 2) or 1e-9
        d_prime = (genuine.mean() - impostor.mean()) / pooled
        print(f'\nDecidability index d\' = {d_prime:.2f} '
              f'({">1 usable" if d_prime > 1 else "<1 weak"} separation)')

    print('\nApply the chosen value in config.yaml -> face.match_threshold')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
