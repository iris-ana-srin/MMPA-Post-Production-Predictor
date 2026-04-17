#data_writer.py

import os
import pandas as pd
from config import OUTPUT_FILE, PREDICTIONS_FILE

class DataWriter:
    def get_last_processed_timestamp(self):
        if not os.path.exists(OUTPUT_FILE):
            return None
        existing = pd.read_csv(OUTPUT_FILE, parse_dates=["production_start_ts"])
        if existing.empty or len(existing) == 1:
            return None
        return existing["production_start_ts"].iloc[-1]

    def append(self, new_df, flag):
        if flag == 1:
            file = PREDICTIONS_FILE
        else:
            file = OUTPUT_FILE

        if os.path.exists(file):
            existing = pd.read_csv(file)
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined.to_csv(file, index=False)
        else:
            new_df.to_csv(file, index=False)