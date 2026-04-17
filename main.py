#main.py

import logging
import json
import pandas as pd

from data_fetcher import DataFetcher
from data_engineer import DataEngineer
from predictor import Predictor
from data_writer import DataWriter
from mqtt_service import MQTTService
from config import RESULT_TOPIC

logging.basicConfig(level=logging.INFO)

fetcher = DataFetcher()
engineer = DataEngineer()
predictor = Predictor()
writer = DataWriter()
predictions = []

def handle_run_end(client, userdata, msg):
    logging.info("EOR Signal Received.")

    last_ts = writer.get_last_processed_timestamp()
    df_states, df_sysdata, df_stagedata = fetcher.fetch(last_ts)

    new_df = engineer.transform(df_states, df_sysdata, df_stagedata, last_ts)
    if new_df is None:
        logging.info("No New Completed Runs.")
        return
    writer.append(new_df, 0)
    logging.info(f"{len(new_df)} Completed Runs added to dataset.csv.")
    
    for _, row in new_df.iterrows():
        pred = predictor.predict(pd.DataFrame([row]))
        if pred is not None:
            if pred > 0.5:
                action = "Likely needed"
            else:
                action = "May be optional"
        else:
            action = None
        predictions.append({
                                'RunId': row['RunId'],
                                'prediction': pred,
                                'action': action
                            })
    writer.append(pd.DataFrame(predictions), 1)      
    logging.info("Predictions saved to predictions.csv")

    client.publish(RESULT_TOPIC, json.dumps(predictions))
    logging.info(f"Prediction Sent: {json.dumps(predictions)}")


if __name__ == "__main__":
    mqtt_service = MQTTService(handle_run_end)
    mqtt_service.start()