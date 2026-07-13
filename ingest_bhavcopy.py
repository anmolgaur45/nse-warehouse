from datetime import datetime
import time

import pandas as pd
from google.cloud import bigquery
from nse import NSE
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

PROJECT_ID = "nse-warehouse"
RAW_DATASET = "raw"
RAW_TABLE = "equity_bhavcopy"


@retry(stop = stop_after_attempt(5), wait = wait_exponential(multiplier=1, min=4, max=10), retry = retry_if_not_exception_type(RuntimeError))

def fetch_bhavcopy_for_date(nse_client, trade_date: datetime) -> pd.DataFrame:
  
    result = nse_client.equityBhavcopy(date=trade_date)
    df = pd.read_csv(result)
    return df
    


def add_ingestion_metadata(df: pd.DataFrame, trade_date: datetime) -> pd.DataFrame:

    df['ingestion_timestamp'] = datetime.now()
    df['trade_date'] = trade_date
    return df


def load_to_bigquery(df: pd.DataFrame, table_id: str) -> None:
    
    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(autodetect=True, write_disposition='WRITE_APPEND')

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)

    job.result()
    



def ingest_date_range(start: datetime, end: datetime, nse_client: NSE) -> None:
    table_id = f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"

    date_list = pd.date_range(start, end)

    failed_dates = []
    execution_dates = 0

    for single_date in date_list:
        try:

            df = fetch_bhavcopy_for_date(nse_client, single_date)

            df = add_ingestion_metadata(df, single_date)

            load_to_bigquery(df, table_id)

            execution_dates += 1

            time.sleep(2)

        except RuntimeError:
            print(f"Runtime error occured for {single_date}")
            continue
        
        except ConnectionError:
            print(f"Connection error occured for {single_date}")
            failed_dates.append(single_date)
            continue
        
        except Exception as e:
            print(f"Some error occured for {single_date}: {repr(e)}")
            failed_dates.append(single_date)
            continue
            
    no_of_failed_dates = len(failed_dates)
    total_dates = execution_dates + no_of_failed_dates
    print(f"{no_of_failed_dates} out of {total_dates} failed to execute. Failed dates: {failed_dates}")


if __name__ == "__main__":

    start_date = datetime(2026, 6, 6)
    end_date = datetime(2026, 6, 30)

    with NSE(download_folder="/tmp/nse_downloads") as nse_client:
        ingest_date_range(start_date, end_date, nse_client)