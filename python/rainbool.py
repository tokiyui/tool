import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
 
def get_daily_precip(year, month, day):
    url = "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php"
    params = {
        "prec_no": 44,
        "block_no": 47662,
        "year": year,
        "month": month,
        "day": day,
        "view": ""
    }
 
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return f"{year},{month},{day},ERROR"
 
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "data2_s"})
    if not table:
        return f"{year},{month},{day},NO_TABLE"
 
    rows = table.find_all("tr")
 
    total_precip = 0.0
    all_dash = True
 
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if not cols:
            continue
 
        try:
            hour = int(cols[0])
        except ValueError:
            continue
 
        if 10 <= hour <= 21:
            precip_str = cols[3]  # 4列目に降水量
            if precip_str in ("-", "－", "", "--"):
                precip = 0.0
            else:
                try:
                    precip = float(precip_str)
                    all_dash = False
                except ValueError:
                    precip = 0.0
            total_precip += precip
 
    if all_dash:
        return f"{year},{month},{day},NaN"
    else:
        return f"{year},{month},{day},{total_precip:.1f}"
 
 
# ループ設定
start_date = datetime(2001, 1, 1)
end_date = datetime(2025, 6, 30)
 
current = start_date
while current <= end_date:
    y, m, d = current.year, current.month, current.day
    result = get_daily_precip(y, m, d)
    print(result)
    current += timedelta(days=1)
