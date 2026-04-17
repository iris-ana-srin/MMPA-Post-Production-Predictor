#predictor.py

import joblib
import logging

logging.basicConfig(level=logging.INFO)

lr = joblib.load("model/junkwash_model.pkl")
scaler = joblib.load("model/junkwash_scaler.pkl")
feature_list = joblib.load("model/feature_list.pkl")

class Predictor:
    def predict(self, df):
        if df is None or df.empty:
            return None
        
        missing_features = set(feature_list) - set(df.columns)
        if missing_features:
            logging.error(f"Missing features for inference: {missing_features}")
            return None
        
        if df[feature_list].isna().any().any():
            logging.warning("NaNs detected, filling with 0")
            return None
        X_new_scaled = scaler.transform(df[feature_list])

        return lr.predict_proba(X_new_scaled)[:, 1][0]