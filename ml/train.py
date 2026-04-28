"""
Water quality ML model trainer.

Trains a classification / regression model to predict future water quality
(E. coli levels, overall bathing water status) based on historical weather
and sea condition features from QuantumLeap / CrateDB.

Output: a serialized model saved to ml/models/water_quality_model.joblib
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("neptuno.ml.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "water_quality_model.joblib"
ECOLI_MODEL_PATH = MODEL_DIR / "ecoli_regressor.joblib"

FEATURE_COLS = [
    "temperature",
    "windSpeed",
    "windDirection",
    "relativeHumidity",
    "precipitation",
    "waveHeight",
    "wavePeriod",
    "seaSurfaceTemperature",
    "pH",
    "salinity",
]


def generate_synthetic_training_data(n_samples: int = 2000) -> pd.DataFrame:
    """Generate realistic synthetic training data when CrateDB history is not
    yet available.

    The synthetic data mimics the statistical distributions of Galician
    coastal weather and water quality conditions, with plausible
    correlations between weather variables and E. coli counts.
    """
    rng = np.random.default_rng(42)

    temperature = rng.normal(16.0, 3.0, n_samples)
    wind_speed = rng.lognormal(2.5, 0.5, n_samples)
    wind_direction = rng.choice([0, 45, 90, 135, 180, 225, 270, 315], n_samples)
    humidity = rng.beta(5, 2, n_samples)
    precipitation = rng.exponential(0.5, n_samples)
    precipitation = np.where(rng.random(n_samples) > 0.3, 0.0, precipitation)

    wave_height = rng.lognormal(-0.2, 0.6, n_samples)
    wave_period = rng.normal(7.0, 2.0, n_samples).clip(3, 15)
    sst = rng.normal(15.5, 2.0, n_samples)
    ph = rng.normal(8.1, 0.15, n_samples)
    salinity = rng.normal(35.0, 0.5, n_samples)

    # E. coli is positively correlated with rain and temperature
    ecoli_base = 30 + 50 * precipitation + 2 * (temperature - 14) + 10 * (humidity - 0.5)
    ecoli = np.maximum(0, rng.poisson(np.maximum(1, ecoli_base)))

    # Classification: good (<200 CFU), acceptable (200-500), poor (>500)
    quality_class = np.where(ecoli < 200, 0, np.where(ecoli < 500, 1, 2))

    df = pd.DataFrame({
        "temperature": np.round(temperature, 1),
        "windSpeed": np.round(wind_speed, 1),
        "windDirection": wind_direction,
        "relativeHumidity": np.round(humidity, 2),
        "precipitation": np.round(precipitation, 1),
        "waveHeight": np.round(wave_height, 2),
        "wavePeriod": np.round(wave_period, 1),
        "seaSurfaceTemperature": np.round(sst, 1),
        "pH": np.round(ph, 2),
        "salinity": np.round(salinity, 1),
        "escherichiaColi": ecoli,
        "qualityClass": quality_class,
    })

    return df


def fetch_training_data_from_cratedb() -> pd.DataFrame | None:
    """Attempt to fetch historical data from CrateDB via QuantumLeap tables."""
    try:
        import httpx

        crate_url = os.getenv("CRATE_URL", "http://localhost:4200")
        sql = """
            SELECT w.temperature, w.windspeed, w.winddirection,
                   w.relativehumidity, w.precipitation,
                   s.waveheight, s.waveperiod, s.seasurfacetemperature,
                   s.ph, s.salinity,
                   q.escherichiacoli, q.intestinalenterococci
            FROM mtsmartbeach.etweatherobserved w
            JOIN mtsmartbeach.etseaconditions s
              ON w.entity_id = s.entity_id AND w.time_index = s.time_index
            JOIN mtsmartbeach.etwaterqualityobserved q
              ON w.entity_id = q.entity_id
            ORDER BY w.time_index DESC
            LIMIT 5000
        """
        resp = httpx.post(f"{crate_url}/_sql", json={"stmt": sql}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            cols = [c["name"] for c in data.get("cols", [])]
            rows = data.get("rows", [])
            if rows:
                df = pd.DataFrame(rows, columns=cols)
                logger.info("Fetched %d rows from CrateDB for training", len(df))
                return df
    except Exception as exc:
        logger.warning("Could not fetch CrateDB training data: %s", exc)
    return None


def train_quality_classifier(df: pd.DataFrame) -> Pipeline:
    """Train a water quality classification model (good/acceptable/poor)."""
    X = df[FEATURE_COLS].values
    y = df["qualityClass"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)

    train_score = pipeline.score(X_train, y_train)
    test_score = pipeline.score(X_test, y_test)
    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy")

    logger.info("Quality Classifier -- Train: %.3f | Test: %.3f | CV: %.3f +/- %.3f",
                train_score, test_score, cv_scores.mean(), cv_scores.std())

    return pipeline


def train_ecoli_regressor(df: pd.DataFrame) -> Pipeline:
    """Train an E. coli count regressor for WaterQualityPredicted."""
    X = df[FEATURE_COLS].values
    y = df["escherichiaColi"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)

    train_score = pipeline.score(X_train, y_train)
    test_score = pipeline.score(X_test, y_test)

    logger.info("E.coli Regressor -- Train R2: %.3f | Test R2: %.3f", train_score, test_score)

    return pipeline


def main() -> None:
    import joblib

    logger.info("Starting ML model training")

    # Try CrateDB first, fall back to synthetic data
    df = fetch_training_data_from_cratedb()
    if df is None or len(df) < 100:
        logger.info("Using synthetic training data (%d samples)", 2000)
        df = generate_synthetic_training_data(2000)
    else:
        # Add qualityClass column
        df["qualityClass"] = np.where(
            df["escherichiaColi"] < 200, 0,
            np.where(df["escherichiaColi"] < 500, 1, 2)
        )
        # Rename columns to match feature list
        rename_map = {
            "windspeed": "windSpeed",
            "winddirection": "windDirection",
            "relativehumidity": "relativeHumidity",
            "waveheight": "waveHeight",
            "waveperiod": "wavePeriod",
            "seasurfacetemperature": "seaSurfaceTemperature",
            "escherichiacoli": "escherichiaColi",
        }
        df = df.rename(columns=rename_map)

    # Train models
    quality_model = train_quality_classifier(df)
    ecoli_model = train_ecoli_regressor(df)

    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(quality_model, MODEL_PATH)
    joblib.dump(ecoli_model, ECOLI_MODEL_PATH)
    logger.info("Models saved to %s", MODEL_DIR)


if __name__ == "__main__":
    main()
