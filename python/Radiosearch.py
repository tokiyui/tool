import requests

base_url = "https://api.radiko.jp/v3/api/program/search?key={}&filter=&start_day=&end_day=&region_id=&cul_area_id=JP13&page_idx=0&uid=72e7122114d9432aa3e976c0a3a7b8a4&row_limit=12&app_id=pc&cur_area_id=JP13&action_id=0"

keywords = ["超ときめき宣伝部", "辻野かなみ", "杏ジュリア", "坂井仁香", "小泉遥香", "菅田愛貴", "吉川ひより", "藤本ばんび" ,"小高サラ", "パブりん"]
programs_set = set()
programs_list = []

for keyword in keywords:
    url = base_url.format(keyword)
    response = requests.get(url)
    data = response.json()

    if "data" in data:
        for program in data["data"]:
            start_time = program.get("start_time")
            program_name = program.get("title")
            station = program.get("station_id")
            program_info = {"start_time": start_time, "program_name": program_name, "station": station}
            program_id = (start_time, program_name, station)
            
            if program_id not in programs_set:
                programs_set.add(program_id)
                programs_list.append(program_info)

# Sort programs by broadcast datetime
sorted_programs = sorted(programs_list, key=lambda x: x["start_time"])

for program in sorted_programs:
    print(f"{program['program_name']}\n{program['start_time']}\n{program['station']}\n")
