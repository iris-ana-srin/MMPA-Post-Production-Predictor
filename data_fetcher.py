#data_fetcher.py

import logging
import pandas as pd
import pyodbc
from dateutil import parser
from config import SQL_CONNECTION_STRING

logging.basicConfig(level=logging.INFO)

class DataFetcher:
    def __init__(self):
        self.conn = None

    def connect(self):
        try:
            self.conn = pyodbc.connect(SQL_CONNECTION_STRING, timeout=60)
            logging.info("Connected to SQL Server.")
        except Exception as e:
            logging.error(f"SQL connection failed: {e}")
            raise

    def fetch(self, last_ts=None):
        stagedata = [] 
        if self.conn is None:
            self.connect()

        if last_ts is not None:
            logging.info(f"Pulling records after {last_ts}")

            for i in range(1, 15): 
                table_name = f"Stage{i}" 
                df = pd.read_sql(f"SELECT * FROM dbo.{table_name} WHERE Timestamp > ? ORDER BY Timestamp", self.conn, params=[last_ts]) 
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
            df_states = pd.read_sql("SELECT * FROM dbo.StateHistory WHERE EndTime > ? ORDER BY StartTime", self.conn, params=[last_ts])
            df_sysdata = pd.read_sql("SELECT Timestamp, PDB, Protein, Solids, MAIN_TOTAL FROM dbo.SystemData WHERE Timestamp > ? ORDER BY Timestamp", self.conn, params=[last_ts])
           
        else:
            logging.info("Pulling full history")

            for i in range(1, 15): 
                table_name = f"Stage{i}" 
                df = pd.read_sql(f"SELECT * FROM dbo.{table_name} ORDER BY Timestamp", self.conn) 
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
            df_states = pd.read_sql("SELECT * FROM dbo.StateHistory ORDER BY StartTime", self.conn)
            df_sysdata = pd.read_sql("SELECT Timestamp, PDB, Protein, Solids, MAIN_TOTAL FROM dbo.SystemData ORDER BY Timestamp", self.conn)

        return df_states, df_sysdata, df_stagedata