"""
AMLIOS-X Machine Learning Models Module

Handles:
- XGBoost risk classification with class imbalance handling
- Precision-Recall AUC evaluation
- Per-account risk probability scoring
- Feature importance extraction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "STUDENT_DATASET"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


@dataclass
class AMLRiskClassifier:
    """Train and score account-level AML risk with an imbalanced XGBoost model.

    The primary Phase 9 input is ``data/processed/node_features.csv`` from the
    graph pipeline. When that file is not ready yet, the classifier can build a
    clean account-level training frame from the provided transaction-level
    ``ml_features.csv`` without touching DevA-owned modules.
    """

    feature_path: str | Path | None = None
    label_col: str | None = None
    account_id_col: str | None = None
    random_state: int = 42
    model_params: dict[str, Any] = field(default_factory=dict)

    model_: Any | None = field(default=None, init=False, repr=False)
    metrics_: dict[str, Any] = field(default_factory=dict, init=False)
    feature_columns_: list[str] = field(default_factory=list, init=False)
    account_id_col_: str | None = field(default=None, init=False)
    label_col_: str | None = field(default=None, init=False)
    training_frame_: pd.DataFrame | None = field(default=None, init=False, repr=False)
    risk_scores_: pd.DataFrame | None = field(default=None, init=False, repr=False)

    TARGET_CANDIDATES = (
        "is_suspicious",
        "is_suspicious_tx",
        "is_laundering",
        "Is_laundering",
        "label",
        "target",
    )
    ACCOUNT_ID_CANDIDATES = (
        "account_id",
        "account",
        "node",
        "node_id",
        "Sender_account",
        "sender_account",
    )
    NON_FEATURE_COLUMNS = {
        "row_index",
        "Date",
        "Time",
        "date_transaction",
        "account_id",
        "account",
        "account_number",
        "Sender_account",
        "Receiver_account",
        "sender_account",
        "receiver_account",
        "name",
        "tax_number",
        "report_id",
        "xml_file",
    }

    def load_features(self, feature_path: str | Path | None = None) -> pd.DataFrame:
        """Load the best available account-level feature table.

        Preference order:
        1. Explicit ``feature_path``
        2. ``data/processed/node_features.csv`` from DevA's graph pipeline
        3. Account-level aggregation from ``data/STUDENT_DATASET/ml_features.csv``
        """

        requested_path = feature_path or self.feature_path
        if requested_path:
            path = Path(requested_path)
        else:
            processed_node_features = PROCESSED_DATA_DIR / "node_features.csv"
            raw_ml_features = RAW_DATA_DIR / "ml_features.csv"
            path = processed_node_features if processed_node_features.exists() else raw_ml_features

        if not path.exists():
            raise FileNotFoundError(f"Feature file not found: {path}")

        df = pd.read_csv(path)
        if self._looks_like_transaction_features(df):
            df = self._aggregate_transaction_features(df)
        else:
            df = self._attach_account_labels_if_needed(df)

        return self._normalize_target(df)

    def train_pipeline(
        self,
        features_df: pd.DataFrame | None = None,
        test_size: float = 0.2,
    ) -> dict[str, Any]:
        """Train the XGBoost classifier and return PR-AUC focused metrics."""

        self._ensure_training_dependencies()

        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import average_precision_score, precision_recall_curve
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
        from xgboost import XGBClassifier

        data = features_df.copy() if features_df is not None else self.load_features()
        data = self._normalize_target(data)
        self.training_frame_ = data.copy()

        target_col = self._infer_target_column(data)
        account_id_col = self._infer_account_id_column(data)
        feature_columns = self._select_feature_columns(data, target_col)

        if not feature_columns:
            raise ValueError("No usable model features found after excluding IDs and labels.")

        X = data[feature_columns].copy()
        y = data[target_col].astype(int)

        class_counts = y.value_counts().to_dict()
        positives = int(class_counts.get(1, 0))
        negatives = int(class_counts.get(0, 0))
        if positives == 0 or negatives == 0:
            raise ValueError(
                "Risk classifier needs both positive and negative labels. "
                f"Observed label counts: {class_counts}"
            )

        stratify = y if y.value_counts().min() >= 2 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=self.random_state,
            stratify=stratify,
        )

        numeric_features = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
        categorical_features = [col for col in feature_columns if col not in numeric_features]

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", SimpleImputer(strategy="median"), numeric_features),
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore")),
                        ]
                    ),
                    categorical_features,
                ),
            ],
            remainder="drop",
        )

        train_positives = int(y_train.sum())
        train_negatives = int(len(y_train) - train_positives)
        scale_pos_weight = train_negatives / max(train_positives, 1)

        xgb_params = {
            "n_estimators": 350,
            "max_depth": 4,
            "learning_rate": 0.04,
            "subsample": 0.9,
            "colsample_bytree": 0.85,
            "min_child_weight": 2,
            "reg_lambda": 1.5,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "scale_pos_weight": scale_pos_weight,
            "random_state": self.random_state,
            "n_jobs": -1,
        }
        xgb_params.update(self.model_params)

        pipeline = Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("model", XGBClassifier(**xgb_params)),
            ]
        )
        pipeline.fit(X_train, y_train)

        risk_probabilities = pipeline.predict_proba(X_test)[:, 1]
        pr_auc = float(average_precision_score(y_test, risk_probabilities))
        precision, recall, thresholds = precision_recall_curve(y_test, risk_probabilities)

        self.model_ = pipeline
        self.feature_columns_ = feature_columns
        self.account_id_col_ = account_id_col
        self.label_col_ = target_col
        self.metrics_ = {
            "pr_auc": pr_auc,
            "baseline_positive_rate": float(y_test.mean()),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "feature_count": int(len(feature_columns)),
            "positive_labels": positives,
            "negative_labels": negatives,
            "scale_pos_weight": float(scale_pos_weight),
            "best_f1_threshold": self._best_f1_threshold(precision, recall, thresholds),
            "label_column": target_col,
            "account_id_column": account_id_col,
        }
        return self.metrics_

    def predict_risk_scores(self, features_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Return ranked per-account risk probabilities and percentile bands."""

        if self.model_ is None:
            raise RuntimeError("Model is not trained. Call train_pipeline() first.")

        if features_df is not None:
            data = features_df.copy()
        elif self.training_frame_ is not None:
            data = self.training_frame_.copy()
        else:
            data = self.load_features()

        data = self._normalize_target(data)
        missing_features = sorted(set(self.feature_columns_) - set(data.columns))
        if missing_features:
            raise ValueError(f"Scoring data is missing trained feature columns: {missing_features}")

        X = data[self.feature_columns_].copy()
        risk_score = np.asarray(self.model_.predict_proba(X))[:, 1]

        account_id_col = self.account_id_col_ or self._infer_account_id_column(data)
        result = pd.DataFrame(
            {
                "account_id": data[account_id_col].astype(str) if account_id_col else data.index.astype(str),
                "risk_score": risk_score,
            }
        )
        result["risk_percentile"] = (result["risk_score"].rank(pct=True) * 100).round(2)
        result["risk_band"] = pd.cut(
            result["risk_score"],
            bins=[-np.inf, 0.25, 0.50, 0.75, 0.90, np.inf],
            labels=["LOW", "ELEVATED", "HIGH", "SEVERE", "CRITICAL"],
        ).astype(str)

        if self.label_col_ and self.label_col_ in data.columns:
            result["actual_label"] = data[self.label_col_].astype(int).to_numpy()

        result = result.sort_values(
            ["risk_score", "risk_percentile"],
            ascending=[False, False],
            kind="mergesort",
        ).reset_index(drop=True)
        result.insert(0, "rank", np.arange(1, len(result) + 1))

        self.risk_scores_ = result
        return result

    def get_feature_importance(self, top_n: int | None = None) -> pd.DataFrame:
        """Return XGBoost feature importances after preprocessing."""

        if self.model_ is None:
            raise RuntimeError("Model is not trained. Call train_pipeline() first.")

        model = self.model_.named_steps["model"]
        preprocessor = self.model_.named_steps["preprocess"]
        feature_names = self._clean_feature_names(preprocessor.get_feature_names_out())
        importances = getattr(model, "feature_importances_", None)
        if importances is None:
            raise RuntimeError("Trained model does not expose feature_importances_.")

        ranking = pd.DataFrame(
            {
                "feature": feature_names,
                "importance": importances,
            }
        ).sort_values("importance", ascending=False, kind="mergesort")

        ranking["importance_rank"] = np.arange(1, len(ranking) + 1)
        return ranking.head(top_n).reset_index(drop=True) if top_n else ranking.reset_index(drop=True)

    def export_risk_scores(
        self,
        output_path: str | Path = PROCESSED_DATA_DIR / "risk_scores.csv",
        features_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Write ranked risk scores to ``data/processed/risk_scores.csv``."""

        scores = self.predict_risk_scores(features_df)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        scores.to_csv(output, index=False)
        return scores

    def export_feature_importance(
        self,
        output_path: str | Path = PROCESSED_DATA_DIR / "feature_importance.csv",
        top_n: int | None = None,
    ) -> pd.DataFrame:
        """Write model feature importance for dashboard/explainability reuse."""

        importance = self.get_feature_importance(top_n=top_n)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        importance.to_csv(output, index=False)
        return importance

    def _aggregate_transaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        label_col = self._infer_target_column(df)
        feature_cols = [
            col
            for col in df.select_dtypes(include=[np.number, "bool"]).columns
            if col not in {label_col, "Sender_account", "Receiver_account", "row_index"}
        ]

        sender_features = self._aggregate_side(
            df,
            account_col="Sender_account",
            feature_cols=feature_cols,
            prefix="sent",
        )
        receiver_features = self._aggregate_side(
            df,
            account_col="Receiver_account",
            feature_cols=feature_cols,
            prefix="received",
        )

        sender_labels = df.groupby("Sender_account")[label_col].max().rename("sender_label")
        receiver_labels = df.groupby("Receiver_account")[label_col].max().rename("receiver_label")

        accounts = (
            pd.Index(df["Sender_account"].dropna().unique())
            .union(pd.Index(df["Receiver_account"].dropna().unique()))
            .rename("account_id")
        )
        account_features = pd.DataFrame(index=accounts)
        account_features = account_features.join(sender_features, how="left")
        account_features = account_features.join(receiver_features, how="left")
        account_features = account_features.join(sender_labels, how="left")
        account_features = account_features.join(receiver_labels, how="left")
        account_features = account_features.fillna(0)

        account_features["is_suspicious"] = account_features[["sender_label", "receiver_label"]].max(axis=1)
        account_features = account_features.drop(columns=["sender_label", "receiver_label"])

        if {"sent_amount_local_npr_sum", "received_amount_local_npr_sum"}.issubset(account_features.columns):
            account_features["net_flow_npr"] = (
                account_features["received_amount_local_npr_sum"]
                - account_features["sent_amount_local_npr_sum"]
            )
            total_flow = (
                account_features["received_amount_local_npr_sum"]
                + account_features["sent_amount_local_npr_sum"]
            ).replace(0, np.nan)
            account_features["inbound_flow_ratio"] = (
                account_features["received_amount_local_npr_sum"] / total_flow
            ).fillna(0)

        return account_features.reset_index()

    def _aggregate_side(
        self,
        df: pd.DataFrame,
        account_col: str,
        feature_cols: list[str],
        prefix: str,
    ) -> pd.DataFrame:
        aggregations: dict[str, list[str]] = {}
        for col in feature_cols:
            if self._is_volume_feature(col):
                aggregations[col] = ["sum", "mean", "max", "std"]
            else:
                aggregations[col] = ["mean", "max"]

        grouped = df.groupby(account_col)[feature_cols].agg(aggregations)
        grouped.columns = [f"{prefix}_{col}_{stat}" for col, stat in grouped.columns]
        grouped[f"{prefix}_tx_count"] = df.groupby(account_col).size()
        return grouped.fillna(0)

    def _attach_account_labels_if_needed(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._find_first_existing(df, self.TARGET_CANDIDATES):
            return df

        account_id_col = self._infer_account_id_column(df)
        raw_ml_features = RAW_DATA_DIR / "ml_features.csv"
        if account_id_col is None or not raw_ml_features.exists():
            return df

        labels = self._aggregate_transaction_features(pd.read_csv(raw_ml_features))
        labels = labels[["account_id", "is_suspicious"]]
        return df.merge(labels, left_on=account_id_col, right_on="account_id", how="left").fillna({"is_suspicious": 0})

    def _normalize_target(self, df: pd.DataFrame) -> pd.DataFrame:
        target = self._find_first_existing(df, self.TARGET_CANDIDATES)
        if target is None:
            return df

        normalized = df.copy()
        if target != "is_suspicious":
            normalized = normalized.rename(columns={target: "is_suspicious"})
        normalized["is_suspicious"] = normalized["is_suspicious"].fillna(0).astype(int).clip(0, 1)
        return normalized

    def _select_feature_columns(self, df: pd.DataFrame, target_col: str) -> list[str]:
        excluded = set(self.NON_FEATURE_COLUMNS)
        excluded.update(self.TARGET_CANDIDATES)
        excluded.add(target_col)

        features = []
        for col in df.columns:
            if col in excluded:
                continue
            if df[col].nunique(dropna=True) <= 1:
                continue
            features.append(col)
        return features

    def _infer_target_column(self, df: pd.DataFrame) -> str:
        if self.label_col and self.label_col in df.columns:
            return self.label_col
        target = self._find_first_existing(df, self.TARGET_CANDIDATES)
        if target:
            return target
        raise ValueError(
            "Could not infer label column. Expected one of: "
            + ", ".join(self.TARGET_CANDIDATES)
        )

    def _infer_account_id_column(self, df: pd.DataFrame) -> str | None:
        if self.account_id_col and self.account_id_col in df.columns:
            return self.account_id_col
        return self._find_first_existing(df, self.ACCOUNT_ID_CANDIDATES)

    def _looks_like_transaction_features(self, df: pd.DataFrame) -> bool:
        required = {"Sender_account", "Receiver_account"}
        return required.issubset(df.columns) and self._find_first_existing(df, self.TARGET_CANDIDATES) is not None

    def _best_f1_threshold(
        self,
        precision: np.ndarray,
        recall: np.ndarray,
        thresholds: np.ndarray,
    ) -> dict[str, float]:
        if len(thresholds) == 0:
            return {"threshold": 0.5, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        aligned_precision = precision[:-1]
        aligned_recall = recall[:-1]
        denominator = aligned_precision + aligned_recall
        f1_scores = np.divide(
            2 * aligned_precision * aligned_recall,
            denominator,
            out=np.zeros_like(denominator),
            where=denominator != 0,
        )
        best_index = int(np.argmax(f1_scores))
        return {
            "threshold": float(thresholds[best_index]),
            "precision": float(aligned_precision[best_index]),
            "recall": float(aligned_recall[best_index]),
            "f1": float(f1_scores[best_index]),
        }

    def _clean_feature_names(self, feature_names: np.ndarray) -> list[str]:
        cleaned = []
        for name in feature_names:
            name = str(name)
            if "__" in name:
                name = name.split("__", 1)[1]
            cleaned.append(name)
        return cleaned

    def _ensure_training_dependencies(self) -> None:
        missing = []
        for package, import_name in {
            "scikit-learn": "sklearn",
            "xgboost": "xgboost",
        }.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package)

        if missing:
            raise ImportError(
                "Missing model training dependencies: "
                + ", ".join(missing)
                + ". Install them with `pip install -r requirements.txt`."
            )

    @staticmethod
    def _find_first_existing(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
        return next((col for col in candidates if col in df.columns), None)

    @staticmethod
    def _is_volume_feature(column: str) -> bool:
        lowered = column.lower()
        return any(
            token in lowered
            for token in (
                "amount",
                "velocity",
                "tx_count",
                "above_",
                "cross_border",
                "currency_mismatch",
            )
        )
