import os
import argparse
import numpy as np
import csv


def load_npz_folder(folder: str):
    for name in os.listdir(folder):
        if name.endswith('.npz'):
            path = os.path.join(folder, name)
            try:
                data = np.load(path)
                feats = data['feats']  # (T, feat_dim)
                labels = data['labels']  # (T,)
                yield name, feats, labels
            except Exception:
                continue


def aggregate_window(feats: np.ndarray) -> np.ndarray:
    if feats.ndim != 2:
        feats = feats.reshape(len(feats), -1)
    mean = feats.mean(axis=0)
    std = feats.std(axis=0)
    rng = (feats.max(axis=0) - feats.min(axis=0))
    return np.concatenate([mean, std, rng], axis=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Folder of dumped npz sequences')
    parser.add_argument('--output', required=True, help='Output CSV of features')
    # accept both --label-rule and --label_rule
    parser.add_argument('--label-rule', '--label_rule', dest='label_rule', choices=['any', 'majority', 'last'], default='majority', help='How to assign window label')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', newline='') as f:
        writer = csv.writer(f)
        header_written = False
        for name, feats, labels in load_npz_folder(args.input):
            if len(feats) == 0:
                continue
            agg = aggregate_window(feats)
            if args.label_rule == 'any':
                y = int((labels > 0).any())
            elif args.label_rule == 'last':
                y = int(labels[-1] > 0)
            else:
                y = int((labels > 0).mean() >= 0.5)
            row = agg.tolist() + [y]
            if not header_written:
                writer.writerow([f'f{i}' for i in range(len(agg))] + ['label'])
                header_written = True
            writer.writerow(row)


if __name__ == '__main__':
    main()


