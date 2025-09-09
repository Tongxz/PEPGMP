import argparse
import os
import csv
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
import joblib


def load_csv(path: str):
    X, y = [], []
    with open(path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            *features, label = row
            X.append([float(v) for v in features])
            y.append(int(label))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', required=True, help='CSV features file')
    parser.add_argument('--out', default='models/handwash_xgb.joblib', help='Output model path')
    args = parser.parse_args()

    X, y = load_csv(args.features)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        n_jobs=-1,
        random_state=42,
        objective='binary:logistic'
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]
    print(classification_report(y_val, y_pred, digits=3))
    try:
        print('AUC:', roc_auc_score(y_val, y_proba))
    except Exception:
        pass

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    joblib.dump(model, args.out)
    print('Saved model to', args.out)


if __name__ == '__main__':
    main()


