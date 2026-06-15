from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import fetch_openml
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
SKLEARN_CACHE_DIR = DATA_DIR / "sklearn_cache"
LOCAL_DATASET_PATH = DATA_DIR / "boston_housing.csv"
RESULTS_CSV_PATH = OUTPUT_DIR / "boston_regression_results.csv"
RESULTS_JSON_PATH = OUTPUT_DIR / "boston_regression_results.json"
ANALYSIS_MD_PATH = OUTPUT_DIR / "boston_regression_analysis.md"

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_SPLITS = 5


def load_boston_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Load Boston Housing from local CSV if present, otherwise fetch and cache it."""
    if LOCAL_DATASET_PATH.exists():
        df = pd.read_csv(LOCAL_DATASET_PATH)
        X = df.drop(columns=["MEDV"])
        y = df["MEDV"]
        return X, y

    X, y = fetch_openml(
        name="boston",
        version=1,
        as_frame=True,
        return_X_y=True,
        data_home=str(SKLEARN_CACHE_DIR),
    )

    df = X.copy()
    df["MEDV"] = pd.to_numeric(y)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(LOCAL_DATASET_PATH, index=False)
    return X, pd.to_numeric(y)


def build_models() -> dict[str, tuple[Pipeline, dict[str, list[float]]]]:
    common_steps = [
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ]

    models = {
        "Lasso": (
            Pipeline(common_steps + [("model", Lasso(max_iter=20000, random_state=RANDOM_STATE))]),
            {"model__alpha": np.logspace(-3, 1, 20).tolist()},
        ),
        "Ridge": (
            Pipeline(common_steps + [("model", Ridge(random_state=RANDOM_STATE))]),
            {"model__alpha": np.logspace(-3, 3, 25).tolist()},
        ),
        "ElasticNet": (
            Pipeline(
                common_steps
                + [("model", ElasticNet(max_iter=20000, random_state=RANDOM_STATE))]
            ),
            {
                "model__alpha": np.logspace(-3, 1, 20).tolist(),
                "model__l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9],
            },
        ),
    }
    return models


def evaluate_models(X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    cv = KFold(n_splits=CV_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    result_rows: list[dict[str, float | str]] = []
    details: dict[str, dict[str, float]] = {}

    for model_name, (pipeline, param_grid) in build_models().items():
        search = GridSearchCV(
            estimator=pipeline,
            param_grid=param_grid,
            scoring="neg_root_mean_squared_error",
            cv=cv,
            n_jobs=-1,
        )
        search.fit(X_train, y_train)

        best_model = search.best_estimator_
        predictions = best_model.predict(X_test)

        rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
        mae = float(mean_absolute_error(y_test, predictions))
        r2 = float(r2_score(y_test, predictions))

        row = {
            "model": model_name,
            "best_params": json.dumps(search.best_params_, ensure_ascii=False),
            "cv_best_rmse": float(-search.best_score_),
            "test_rmse": rmse,
            "test_mae": mae,
            "test_r2": r2,
        }
        result_rows.append(row)

        details[model_name] = {
            "cv_best_rmse": float(-search.best_score_),
            "test_rmse": rmse,
            "test_mae": mae,
            "test_r2": r2,
            "best_params": search.best_params_,
        }

    results_df = pd.DataFrame(result_rows).sort_values(
        by=["test_rmse", "test_mae", "test_r2"],
        ascending=[True, True, False],
    )
    return results_df, details


def build_analysis_markdown(results_df: pd.DataFrame) -> str:
    best_row = results_df.iloc[0]
    worst_row = results_df.iloc[-1]

    lasso = results_df.loc[results_df["model"] == "Lasso"].iloc[0]
    ridge = results_df.loc[results_df["model"] == "Ridge"].iloc[0]
    elastic = results_df.loc[results_df["model"] == "ElasticNet"].iloc[0]

    display_df = results_df.copy()
    for col in ["cv_best_rmse", "test_rmse", "test_mae", "test_r2"]:
        display_df[col] = display_df[col].map(lambda value: f"{value:.4f}")

    header = "| 模型 | 最优参数 | 交叉验证RMSE | 测试集RMSE | 测试集MAE | 测试集R² |"
    separator = "| --- | --- | ---: | ---: | ---: | ---: |"
    rows = [
        f"| {row.model} | `{row.best_params}` | {row.cv_best_rmse} | {row.test_rmse} | {row.test_mae} | {row.test_r2} |"
        for row in display_df.itertuples(index=False)
    ]
    markdown_table = "\n".join([header, separator, *rows])

    return f"""# Boston 房价预测模型对比分析

## 实验说明

- 数据集：Boston Housing（OpenML `boston` version 1）
- 样本数：506
- 特征数：13
- 目标变量：`MEDV`（房价中位数）
- 训练测试划分：80% 训练集，20% 测试集，`random_state=42`
- 预处理：中位数填补 + 标准化
- 调参方法：5 折交叉验证，优化指标为 RMSE

> 说明：Boston 数据集因公平性争议已被官方弃用，这里仅用于完成课程/实验中的回归方法比较。

## 指标结果

{markdown_table}

## 结果分析

- 从测试集 RMSE 和 MAE 来看，**{best_row["model"]}** 的预测效果最好，测试集 RMSE 为 **{best_row["test_rmse"]:.4f}**，R² 为 **{best_row["test_r2"]:.4f}**。
- 表现最弱的是 **{worst_row["model"]}**，说明在当前划分和参数范围下，它对 Boston 数据集的拟合能力相对更弱。
- **Ridge 回归** 的测试集 R² 为 **{ridge["test_r2"]:.4f}**，整体表现稳定。它通过 L2 正则化抑制系数过大，适合处理多重共线性较明显的数据。
- **Lasso 回归** 的测试集 R² 为 **{lasso["test_r2"]:.4f}**。L1 正则化会压缩部分系数，甚至把一些特征系数压到 0，因此具备一定特征选择能力，但在这个数据集上精度略逊于最优模型。
- **ElasticNet 回归** 结合了 L1 与 L2 正则化，测试集 R² 为 **{elastic["test_r2"]:.4f}**。它通常在“需要稀疏性”与“需要稳定性”之间取得折中。

## 结论

- 如果目标是 **追求当前实验中的最佳预测精度**，优先选择 **{best_row["model"]}**。
- 如果更关注 **模型稳定性和抗多重共线性能力**，Ridge 回归通常是很稳妥的选择。
- 如果希望 **自动筛选特征、得到更稀疏的模型**，Lasso 或 ElasticNet 更合适。
- 综合这次实验结果，三种方法都能完成房价预测任务，但 **{best_row["model"]} 在本次实验中综合表现最好**。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_boston_dataset()
    results_df, details = evaluate_models(X, y)

    results_df.to_csv(RESULTS_CSV_PATH, index=False, encoding="utf-8-sig")
    RESULTS_JSON_PATH.write_text(
        json.dumps(details, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ANALYSIS_MD_PATH.write_text(
        build_analysis_markdown(results_df),
        encoding="utf-8",
    )

    print("Boston Housing regression comparison completed.")
    print(results_df.to_string(index=False))
    print(f"\nSaved CSV: {RESULTS_CSV_PATH}")
    print(f"Saved JSON: {RESULTS_JSON_PATH}")
    print(f"Saved Markdown analysis: {ANALYSIS_MD_PATH}")


if __name__ == "__main__":
    main()
