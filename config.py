# config.py

BROKER = "localhost"
PORT = 1883
TRIGGER_TOPIC = "uf1/run_end"
RESULT_TOPIC = "uf1/junkwash_prediction"

OUTPUT_FILE = "dataset.csv"
PREDICTIONS_FILE = "predictions.csv"

SQL_CONNECTION_STRING = (
                            "DRIVER={ODBC Driver 17 for SQL Server};"
                            "SERVER=dataview1.database.windows.net;"
                            "DATABASE=Iris-Constantine;"
                            "UID=IrisAdmin;"
                            "PWD=Kendall1!"
                        )