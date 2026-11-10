import os
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

# 1. 設定項目
TARGET_URL = "https://github.com/orgs/google/repositories"
DB_PATH = os.path.join("db", "github_repos.db")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def prepare_db_path() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        if os.path.exists(db_dir) and not os.path.isdir(db_dir):
            os.remove(db_dir)
        os.makedirs(db_dir, exist_ok=True)


def fetch_repository_page(url: str) -> BeautifulSoup:
    # 課題要件: サーバー負担軽減のためアクセス前に1秒待機
    time.sleep(1)
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_repository_data(soup: BeautifulSoup):
    repositories = []

    # リポジトリのリンクを取得
    repo_links = soup.select("a[itemprop='name codeRepository']")
    if not repo_links:
        repo_links = [a for a in soup.select("h3 a") if "/google/" in a.get("href", "")]

    for a_tag in repo_links:
        name = a_tag.get_text(strip=True)

        # ①リポジトリ枠（カード全体の親要素）を取得
        card = a_tag.find_parent("li")
        if not card:
            card = a_tag.find_parent("div", class_=lambda c: c and "Box" in c)
        if not card and a_tag.parent:
            card = a_tag.parent.parent

        language = "N/A"
        stars = "0"

        if card:
            # ② 主要言語の抽出 (様々なHTMLパターンを網羅)
            lang_elem = (
                card.find(attrs={"itemprop": "programmingLanguage"})
                or card.select_one('[data-filterable-for] span[class*="color"]')
                or card.select_one("span[class*='language']")
            )
            
            if lang_elem:
                language = lang_elem.get_text(strip=True)
            else:
                # itempropで見つからない場合、言語ドット（span.repo-language-colorなど）の隣のテキストを取得
                color_dot = card.select_one("span.repo-language-color, span[style*='background-color']")
                if color_dot and color_dot.next_sibling:
                    language = color_dot.next_sibling.text.strip()

            # ③ Starsの抽出
            star_elem = card.select_one('a[href*="/stargazers"]') or card.select_one('a[href*="/stargazer"]')
            if star_elem:
                stars = star_elem.get_text(strip=True).replace(",", "")

        repositories.append((name, language, stars))

    return repositories


def save_repositories(repositories):
    prepare_db_path()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 既存のテーブルを一旦削除してIDを1からリセットできるようにする
        cursor.execute("DROP TABLE IF EXISTS repositories")
        
        cursor.execute(
            """
            CREATE TABLE repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                language TEXT,
                stars TEXT
            )
            """
        )

        for name, language, stars in repositories:
            cursor.execute(
                "INSERT INTO repositories (name, language, stars) VALUES (?, ?, ?)",
                (name, language, stars),
            )

        conn.commit()

        # 課題要件: SELECT文を使って保存データを取得・画面表示する
        print("=== SQLite保存データ (SELECT文実行結果) ===")
        cursor.execute("SELECT id, name, language, stars FROM repositories")
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | リポジトリ名: {row[1]} | 言語: {row[2]} | Stars: {row[3]}")


def main():
    try:
        soup = fetch_repository_page(TARGET_URL)
    except requests.RequestException as exc:
        print(f"Web fetch failed: {exc}. Continuing with an empty dataset.")
        soup = BeautifulSoup("", "html.parser")

    repositories = extract_repository_data(soup)
    print(f"取得できた件数: {len(repositories)} 件")
    save_repositories(repositories)


if __name__ == "__main__":
    main()