import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 設定
# ============================================================

# 調査対象の人物名をここに追加 
PERSONS = ["超ときめき宣伝部"]

BASE_URL = "https://www.fujisan.co.jp"
SEARCH_PATH = "/zasshi_search/"

LIMIT = 12
OUTPUT_DIR = Path("fujisan_results")
HTML_DIR = OUTPUT_DIR / "html"

# アクセス負荷を抑えるための待機時間（秒）
WAIT_SECONDS = 1.5
TIMEOUT = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HTML_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HTTPセッション
# ============================================================

session = requests.Session()

retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
})


# ============================================================
# 共通関数
# ============================================================

def build_search_url(person, page=1):
    """人物名とページ番号から検索URLを作成する。"""
    params = {
        "limit": LIMIT,
        "page": page,
        "qk": person,
        "t": "s",
        "tb": "c",
    }
    return BASE_URL + SEARCH_PATH + "?" + urlencode(params)


def safe_filename(name):
    """ファイル名に使用できない文字を置換する。"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def get_text(element):
    """要素内の文字列を取得する。"""
    return element.get_text(" ", strip=True) if element else ""


def fetch_page(url):
    """HTMLを取得する。"""
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def get_next_page_url(soup, current_url):
    """ページネーションから次ページURLを取得する。"""

    # rel="next" がある場合は優先
    next_link = soup.select_one('link[rel="next"][href]')
    if next_link:
        return urljoin(current_url, next_link["href"])

    # 実際のページネーションの「次のページ」リンク
    for link in soup.select(".paging a[href]"):
        text = get_text(link)
        if "次のページ" in text or text in ("次へ", "次 ›", "次 »"):
            return urljoin(current_url, link["href"])

    return None


def extract_results(soup, person):
    """検索結果一覧から雑誌情報を抽出する。"""
    results = []

    for card in soup.select("div.card-book.search-list"):
        name_element = card.select_one(
            ".card-book-name.search-product-name"
        )

        # 商品名のリンク
        product_link = card.select_one('a[href*="/product/"]')
        product_name = get_text(name_element)

        if not product_name and product_link:
            product_name = get_text(product_link)

        product_url = (
            urljoin(BASE_URL, product_link["href"])
            if product_link and product_link.get("href")
            else ""
        )

        description = card.select_one(".card-book-description")
        comment = card.select_one(".search-comment")

        image = card.select_one("img.search-image")
        image_url = ""
        if image:
            image_url = (
                image.get("data-original")
                or image.get("data-src")
                or image.get("src")
                or ""
            )
            if image_url:
                image_url = urljoin(BASE_URL, image_url)

        cover_names = [
            get_text(item)
            for item in card.select(".cover-tag-names-links a span")
            if get_text(item)
        ]

        results.append({
            "person": person,
            "magazine_name": product_name,
            "release_info": get_text(description),
            "excerpt": get_text(comment),
            "cover_names": " / ".join(dict.fromkeys(cover_names)),
            "product_url": product_url,
            "image_url": image_url,
        })

    return results


# ============================================================
# 人物1人分の全ページ取得
# ============================================================

def scrape_person(person):
    print(f"\n{'=' * 60}")
    print(f"検索開始: {person}")
    print("=" * 60)

    current_url = build_search_url(person, 1)
    visited_urls = set()
    seen_products = set()
    all_results = []

    page_number = 0

    while current_url:
        # 同一URLの無限巡回を防止
        if current_url in visited_urls:
            print(f"[警告] 同一URLを検出。巡回を終了: {current_url}")
            break

        visited_urls.add(current_url)
        page_number += 1

        print(f"[{person}] ページ {page_number}: {current_url}")

        try:
            html = fetch_page(current_url)
        except requests.RequestException as e:
            print(f"[エラー] ページ取得失敗: {e}")
            print("この人物の処理を中断します。")
            break

        # 取得したHTMLを保存（後から再解析できる）
        html_path = (
            HTML_DIR
            / f"{safe_filename(person)}_page_{page_number:04d}.html"
        )
        html_path.write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "html.parser")
        page_results = extract_results(soup, person)

        if not page_results:
            print(
                f"[警告] ページ {page_number} から結果を抽出できません。"
                "HTMLを保存しました。"
            )

        added = 0

        for item in page_results:
            # 商品URLを優先して重複排除
            unique_key = item["product_url"] or (
                item["magazine_name"],
                item["release_info"],
            )

            if unique_key in seen_products:
                continue

            seen_products.add(unique_key)
            all_results.append(item)
            added += 1

        print(
            f"  抽出: {len(page_results)}件 / "
            f"新規追加: {added}件 / "
            f"累計: {len(all_results)}件"
        )

        next_url = get_next_page_url(soup, current_url)

        # 次ページURLが取得できない場合、最終ページと断定せず記録する
        if not next_url:
            print(
                f"[情報] 次ページリンクなし。"
                f"ページ {page_number} で巡回を終了します。"
            )
            break

        current_url = next_url
        time.sleep(WAIT_SECONDS)

    print(f"[完了] {person}: {len(all_results)}件")
    return all_results


# ============================================================
# CSV / JSONL 出力
# ============================================================

FIELDS = [
    "person",
    "magazine_name",
    "release_info",
    "excerpt",
    "cover_names",
    "product_url",
    "image_url",
]


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def save_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ============================================================
# 全人物を一括処理
# ============================================================

def main():
    all_results = []

    for index, person in enumerate(PERSONS, start=1):
        print(f"\n人物 {index}/{len(PERSONS)}")

        try:
            rows = scrape_person(person)
        except Exception as e:
            print(f"[予期しないエラー] {person}: {e}")
            continue

        all_results.extend(rows)

        # 人物ごとのファイル
        filename = safe_filename(person)
        save_csv(OUTPUT_DIR / f"{filename}.csv", rows)
        save_jsonl(OUTPUT_DIR / f"{filename}.jsonl", rows)

        # 途中経過も全員分のファイルに反映
        save_csv(OUTPUT_DIR / "all_persons.csv", all_results)
        save_jsonl(OUTPUT_DIR / "all_persons.jsonl", all_results)

    print("\n" + "=" * 60)
    print("全人物の処理終了")
    print(f"対象人物数: {len(PERSONS)}")
    print(f"取得件数合計: {len(all_results)}")
    print(f"出力先: {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
