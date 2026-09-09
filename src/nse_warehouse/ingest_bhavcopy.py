from datetime import datetime, timezone
import time
import os
import argparse

import pandas as pd
from google.cloud import bigquery
from nse import NSE
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

PROJECT_ID = os.environ["PROJECT_ID"]
RAW_DATASET = os.environ["RAW_DATASET"]
RAW_TABLE = "equity_bhavcopy"

SCHEMA_PATH = "schemas/equity_bhavcopy.json"
STAGING_EXPIRY_HOURS = 72

LEGACY_COLUMN_MAP = {
    'SYMBOL': 'TckrSymb',
    'SERIES': 'SctySrs',
    'OPEN': 'OpnPric',
    'CLOSE': 'ClsPric',
    'HIGH': 'HghPric',
    'LOW': 'LwPric',
    'TOTTRDQTY': 'TtlTradgVol',
    'TOTTRDVAL': 'TtlTrfVal',
    'TOTALTRADES': 'TtlNbOfTxsExctd',
    'LAST': 'LastPric',
    'PREVCLOSE': 'PrvsClsgPric'
}
 
class NoDataForDate(Exception):
    '''NSE published no file for this date. Expected on weekends and holidays.'''
    pass

def is_legacy_format(df: pd.DataFrame) -> bool:
    return 'SYMBOL' in df.columns
 
 
def normalize_legacy_format(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=LEGACY_COLUMN_MAP).drop(columns=['TIMESTAMP', 'Unnamed: 13'], errors='ignore')
    df['FinInstrmNm'] = df['TckrSymb'].copy()
    df['name_is_placeholder'] = True
    return df

@retry(stop = stop_after_attempt(5), wait = wait_exponential(multiplier=1, min=4, max=10), retry = retry_if_not_exception_type(RuntimeError))
def fetch_bhavcopy_for_date(nse_client, trade_date: datetime) -> pd.DataFrame:
  
    result = nse_client.equityBhavcopy(date=trade_date)
    df = pd.read_csv(result)
    if is_legacy_format(df):
        df = normalize_legacy_format(df)
    else:
        df['name_is_placeholder'] = False
    return df
    


def add_ingestion_metadata(df: pd.DataFrame, trade_date: datetime) -> pd.DataFrame:

    df['ingestion_timestamp'] = datetime.now(timezone.utc)
    df['trade_date'] = trade_date
    return df


def load_to_bigquery(df: pd.DataFrame, table_id: str) -> None:
    
    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        autodetect=True, 
        write_disposition='WRITE_APPEND',
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
    )

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)

    job.result()
    
def ingest_single_date(trade_date: datetime, nse_client: NSE) -> None:
    table_id = f"{PROJECT_ID}.{RAW_DATASET}.{RAW_TABLE}"

    try:
        df = fetch_bhavcopy_for_date(nse_client, trade_date)
        df = add_ingestion_metadata(df, trade_date)
        load_to_bigquery(df, table_id)
    except RuntimeError as e:
        print(f"Runtime error occured for {trade_date}")
        raise NoDataForDate(f"No NSE data available for {trade_date}") from e
    except Exception as e:
        print(f"Error occured for {trade_date}: {repr(e)}")
        raise


def ingest_date_range(start: datetime, end: datetime, nse_client: NSE) -> None:

    date_list = pd.date_range(start, end)

    failed_dates = []
    holiday_dates = []
    execution_dates = 0

    for idx, single_date in enumerate(date_list):
        if idx > 0:
            time.sleep(2)

        try:
            ingest_single_date(single_date, nse_client)
            execution_dates += 1
        except NoDataForDate:
            print(f"No data found for {single_date}")
            holiday_dates.append(single_date)
        except ConnectionError:
            print(f"Connection error occured for {single_date}")
            failed_dates.append(single_date)
            continue
        except Exception as e:
            print(f"Some error occured for {single_date}: {repr(e)}")
            failed_dates.append(single_date)
            continue
            
    no_of_failed_dates = len(failed_dates)
    no_of_holidays = len(holiday_dates)
    total_dates = execution_dates + no_of_failed_dates + no_of_holidays
    print(f"Processed: {execution_dates}/{total_dates} | Holidays: {len(holiday_dates)} | Critical Failures: {no_of_failed_dates}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Ingest NSE Bhavcopy data into BigQuery.')
    parser.add_argument(
        '--date',
        type=lambda s: datetime.fromisoformat(s),
        required=True
    )
    args = parser.parse_args()

    with NSE(download_folder="/tmp/nse_downloads") as nse_client:

        ingest_single_date(args.date, nse_client)
