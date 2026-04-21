#data_fetcher.py

import logging
import pandas as pd
import pyodbc
from datetime import timedelta
from config import SQL_CONNECTION_STRING

logging.basicConfig(level=logging.INFO)

class DataFetcher:
    def __init__(self):
        self.conn_str = SQL_CONNECTION_STRING

    def fetch(self, last_ts=None):
        stagedata = [] 
        conn = None
        try:
            logging.info("Connecting to SQL Server...")
            conn = pyodbc.connect(self.conn_str, timeout=60)

            if not pd.isna(last_ts):
                logging.info(f"Pulling records after {last_ts}...")

                for i in range(1, 15): 
                    table_name = f"Stage{i}" 
                    df = pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE Timestamp >= ? ORDER BY Timestamp", conn, params=[last_ts]) 
                    df = df.drop(columns=['LocalTimestamp', 'Id'])
                    df["Stage"] = i
                    stagedata.append(df) 
                final_df = pd.concat(stagedata, ignore_index=True) 
                final_df = final_df[[ "Timestamp", 
                                    "Stage", 
                                    "DFFlowRate", 
                                    "BoosterPumpCurrent", 
                                    "BoostPressure", 
                                    "Temperature",
                                    "PermeateFlowRate", 
                                    "SurfaceArea", 
                                    "PressureDrop", 
                                    "TransmembranePressure", 
                                    "Permeance"]] 
                
                df_stagedata = final_df.sort_values(by=["Timestamp", "Stage"]).reset_index(drop=True) 
                df_states = pd.read_sql("SELECT * FROM dbo.StateHistory WHERE StartTime >= ? ORDER BY StartTime", conn, params=[last_ts - timedelta(hours=2)])
                df_sysdata = pd.read_sql("SELECT Timestamp, PDB, Protein, Solids, MAIN_TOTAL FROM dbo.SystemData WHERE Timestamp >= ? ORDER BY Timestamp", conn, params=[last_ts])
            
            else:
                logging.info("Pulling full history...")

                for i in range(1, 15): 
                    table_name = f"Stage{i}" 
                    df = pd.read_sql(f"SELECT * FROM dbo.{table_name} ORDER BY Timestamp", conn) 
                    df = df.drop(columns=['LocalTimestamp', 'Id'])
                    df["Stage"] = i
                    stagedata.append(df) 
                final_df = pd.concat(stagedata, ignore_index=True) 
                final_df = final_df[[ "Timestamp", 
                                    "Stage", 
                                    "DFFlowRate", 
                                    "BoosterPumpCurrent", 
                                    "BoostPressure", 
                                    "Temperature",
                                    "PermeateFlowRate", 
                                    "SurfaceArea", 
                                    "PressureDrop", 
                                    "TransmembranePressure", 
                                    "Permeance"]] 
                
                df_stagedata = final_df.sort_values(by=["Timestamp", "Stage"]).reset_index(drop=True) 
                df_states = pd.read_sql("SELECT * FROM dbo.StateHistory ORDER BY StartTime", conn)
                df_sysdata = pd.read_sql("SELECT Timestamp, PDB, Protein, Solids, MAIN_TOTAL FROM dbo.SystemData ORDER BY Timestamp", conn)

            return df_states, df_sysdata, df_stagedata
        
        except Exception as e:
            logging.exception(f"Fetch failed: {e}")
            raise

        finally:
            if conn is not None:
                conn.close()
                logging.info("SQL connection closed.")