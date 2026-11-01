import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path.cwd()
data = pd.read_csv(ROOT / "data/frozen/v1/ecoli_phenotype_mlst_v1.csv")
splits = pd.read_csv(ROOT / "data/processed/ecoli_baseline_split_v1.csv")

data = data.merge(splits, on="BioSample", validate="many_to_one")

results = {}

for drug in ["ciprofloxacin", "ceftriaxone", "gentamicin"]:
    df = data[data["Drug"] == drug].copy()

    train = df[df["Split"] == "train"]
    validation = df[df["Split"] == "validation"]

    X_train = train[["ST"]].astype(str)
    X_val = validation[["ST"]].astype(str)

    y_train = (train["Phenotype"] == "resistant").astype(int)
    y_val = (validation["Phenotype"] == "resistant").astype(int)

    model = Pipeline([
        ("features", ColumnTransformer([
            ("st", OneHotEncoder(handle_unknown="ignore"), ["ST"])
        ])),
        ("classifier", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ))
    ])

    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_val)[:, 1]

    metrics = {
        "train_samples": len(train),
        "validation_samples": len(validation),
        "validation_roc_auc": round(float(roc_auc_score(y_val, probabilities)), 4),
        "validation_pr_auc": round(float(average_precision_score(y_val, probabilities)), 4),
        "validation_resistance_prevalence": round(float(y_val.mean()), 4),
    }

    results[drug] = metrics

    print(f"\n{drug.upper()}")
    for key, value in metrics.items():
        print(f"{key}: {value}")

output = ROOT / "results/baseline/lineage_baseline_v1.json"
output.write_text(json.dumps(results, indent=2))

print("\nResults saved:", output)
print("TEST SET: NOT USED")
