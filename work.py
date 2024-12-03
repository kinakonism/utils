from datetime import datetime, timedelta
import calendar
import jpholiday
import pandas as pd
from notion import get_rows_to_dataframe, insert_rows_from_dict


def _set_objective_date(year: int, month: int) -> datetime:
    """稼働日を計算したい年月を設定
    """
    if year is None and month is None:
        objective_date = datetime.today()
    elif year is not None and month is None:
        objective_date = datetime(year, datetime.now().month, 1)
    elif year is None and month is not None:
        objective_date = datetime(datetime.now().year, month, 1)
    else:
        objective_date = datetime(year, month, 1)
    
    return objective_date


def _judge_adding_extra_time(working_day: int) -> bool:
    """所定の稼働日20日(160時間)を下回るかを判定
    """
    default_working_day = 20
    if working_day < default_working_day:
        need_days = default_working_day - working_day
        need_hour_per_day = round(need_days * 8 / working_day, 1)
        print(f"稼働日数が{working_day}日で稼働時間が {working_day * 8}h となり、所定稼動時間(160h)まで{160 - working_day * 8}時間足りません。")
        print(f"1日あたり約{need_hour_per_day}時間({round(need_hour_per_day * 60)}分)の残業が必要です。")
        return True
    else:
        print(f"稼働日数が{working_day}日で稼働時間が {working_day * 8}h >= 160h により、残業の必要はありません。")
    
        return False


def get_working_day(year: int=None, month: int=None, off: int=0) -> bool:
    """年月から稼働時間を計算
    """
    objective_date = _set_objective_date(year, month)
    print(f"\n{objective_date.strftime("%Y年%m月")}の稼働日について確認します。")

    # get holiday
    holidays = [h[0] for h in jpholiday.month_holidays(objective_date.year, objective_date.month)]
    # get weekend
    c = calendar.Calendar()
    weekends = [w for w in list(c.itermonthdates(objective_date.year, objective_date.month)) if w.month == objective_date.month and w.weekday() in [5, 6]]
    # merge
    merged_dates = sorted(list(set(holidays + weekends)), key=lambda d: d.day)
    month_days = calendar.monthrange(objective_date.year, objective_date.month)[1]
    working_day = month_days - len(merged_dates)
    real_working_day = working_day - off
    print("-----------------------------------------------")
    print(f"{objective_date.year}年{objective_date.month}月の稼働日サマリー")
    print("-----------------------------------------------")
    print(f"月日数: {month_days}日, 土日祝日: {len(merged_dates)}日, 休暇: {str(off) + "日" if off > 0 else "なし"}")
    print(f"所定の稼働日: {working_day}日, 所定の稼働時間: {working_day * 8}h")
    if off:
        print(f"見込み稼働日: {real_working_day}日, 見込み稼働時間: {real_working_day * 8}h")
    else:
        print("取得する休暇は無いので、所定稼働時間が見込み稼働時間になります。")
    print("-----------------------------------------------")
    
    return _judge_adding_extra_time(real_working_day)


def round_time_to_nearest_15min(dt):
    """分を15分刻みで丸める
    """
    minute = dt.minute
    delta = (minute + 5) // 15 * 15 - minute
    rounded_dt = dt + timedelta(minutes=delta)

    return rounded_dt.replace(second=0, microsecond=0)


def report_working_time(today: datetime, start_time: str, end_time: str, rest: str="01:00", content: str="自動化対応"):
    """退勤時間を記録
    """
    # calculate work time
    work_time = pd.to_datetime(end_time) - pd.to_datetime(start_time) - timedelta(hours=1)
    work_time = str(work_time).split()[2][:5]
    # prepare row
    inserted_dict = {
        "date": today.strftime("%Y/%m/%d"),
        "start_time": start_time,
        "end_time": end_time,
        "rest": rest,
        "work_time": work_time,
        "content": content
    }
    df_work_time = pd.DataFrame(inserted_dict, index=[0])
    print(df_work_time)
    # output csv
    df_work_time.to_csv(f"./work_time/work_time_{today.strftime("%Y%m")}.csv", index=False, mode='a', header=False)
    # insert notion
    insert_rows_from_dict(inserted_dict)


def _get_h_m_s(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)

    return h, m, s


def calc_current_work_time(today: datetime):
    """現在の稼働時間を取得・計算
    """
    # # notionから取得するように変更したのでコメントアウト
    # csv
    # current_times = pd.read_csv(f"./work_time/work_time_{today.strftime("%Y%m")}.csv", header=None, names=["date", "start_time", "end_time", "rest", "work_time", "content"])
    # print(current_times)
    # current_times["work_time_str_org"] = current_times["work_time"]
    # current_times["work_time"] = pd.to_datetime(current_times["end_time"]) - pd.to_datetime(current_times["start_time"]) - timedelta(hours=1)
    # current_times["work_time_str"] = current_times["work_time"].apply(lambda x: str(x).split()[2][:5])
    # assert (current_times["work_time_str_org"] == current_times["work_time_str"]).all()
    # day_to_hour = current_times["work_time"].sum().days * 24
    # hour, minute, _ = _get_h_m_s(current_times["work_time"].sum().seconds)
    # total_work_time =  day_to_hour + hour
    # last_date = current_times["date"].max()

    # notion
    res = get_rows_to_dataframe(keys=["date", "start_time", "end_time", "rest", "work_time"])
    rows = res.dropna().sort_values("date").reset_index(drop=True)
    # 今月のみに絞る
    rows["date_dt"] = pd.to_datetime(rows["date"])
    current_times = rows[rows["date_dt"].dt.month == today.month].copy()
    current_times["work_time_hour_int"] = current_times["work_time"].apply(lambda x: int(x.split(":")[0]))
    current_times["work_time_min_int"] = current_times["work_time"].apply(lambda x: int(x.split(":")[1]))
    total_work_time_hour =  current_times["work_time_hour_int"].sum() + current_times["work_time_min_int"].sum() / 60
    total_hour = int(total_work_time_hour)
    total_min = (total_work_time_hour - total_hour) * 60
    last_date = current_times["date"].max()
    print(f"{last_date}時点での合計稼働日数は{current_times.shape[0]}日、合計稼働時間は{total_hour}時間{round(total_min)}分です。")


if __name__ == "__main__":
    # example
    new_year_off_days = 2
    private_off_days = 1
    off_days = new_year_off_days + private_off_days
    get_working_day(month=1, off=off_days)

    # dt = datetime(2024, 10, 1)
    dt = datetime.today()
    calc_current_work_time(dt)
    
    # report_working_time(dt, "10:00", "20:00")