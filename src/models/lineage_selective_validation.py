import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

data = pd.read_csv("data/frozen/v1/ecoli_phenotype_mlst_v1.csv")
splits = pd.read_csv("data/processed/ecoli_baseline_split_v1.csv")
data = data.merge(splits, on="BioSample", validate="many_to_one")

thresholds = [0.01, 0.05, 0.10, 0.20, 0.30, 0.50]

for drug in ["ciprofloxacin", "ceftriaxone", "gentamicin"]:
    df = data[data["Drug"] == drug]
    train = df[df["Split"] == "train"]
    val = df[df["Split"] == "validation"]

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

    model.fit(
        train[["ST"]].astype(str),
        (train["Phenotype"] == "resistant").astype(int)
    )

    probabilities = model.predict_proba(val[["ST"]].astype(str))[:, 1]
    resistant = (val["Phenotype"] == "resistant").to_numpy()

    print(f"\n{drug.upper()}")
    print(f"{'Threshold':>10} {'Reported':>10} {'Coverage':>10} {'False-S':>10} {'Risk %':>10}")

    for threshold in thresholds:
        report = probabilities <= threshold
        n = int(report.sum())
        false_s = int((resistant & report).sum())
        coverage = n / len(val)
        risk = false_s / n if n else float("nan")

        print(
            f"{threshold:>10.2f} {n:>10} "
            f"{coverage:>9.1%} {false_s:>10} {risk:>9.2%}"
        )

print("\nTEST SET: NOT USED")
