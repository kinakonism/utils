import os
from datetime import datetime, timedelta
import json
import jinja2
from dotenv import load_dotenv
load_dotenv()
from notion_client import Client
from pprint import pprint
import pandas as pd

# read jinja template 
loader = jinja2.FileSystemLoader('.')
template = jinja2.Environment(loader=loader).get_template(name='properties.json')
# notion settings
notion = Client(auth=os.environ['NOTION_TOKEN'])
database_id = os.environ['DATABASE_ID']


def get_rows_to_dataframe(keys: list[str]) -> pd.DataFrame:
    db = notion.databases.query(
        **{
            'database_id' : database_id
           }
    )    
    response = pd.DataFrame([
            {
                k: db["results"][idx]["properties"][k]["rich_text"][0]["text"]["content"]
                for k in keys if db["results"][idx]["properties"][k].get("rich_text")
            }
            for idx in range(len(db["results"]))
        ])
    
    return response


def insert_rows_from_dict(inserted: dict):
    pprint(inserted)
    properties = template.render(inserted_dict=inserted)
    
    notion.pages.create(
        **{
            'parent': {'database_id': database_id},
            'properties': json.loads(properties)
        }
    )


if __name__ == "__main__":
    # # example
    # inserted_dict = {
    #         "date": "2024/11/01",
    #         # "date": datetime.today().strftime("%Y/%m/%d"),
    #         "start_time": "10:00",
    #         "end_time": "20:00",
    #         "rest": "01:00",
    #         "content": "リファクタリング"
    #     }
    # insert_rows_from_dataframe(inserted_dict)

    res = get_rows_to_dataframe(keys=["date", "start_time", "end_time", "rest", "work_time", "content"])
    work_times = res.dropna().reset_index(drop=True)
    print(work_times.sort_values("date"))
