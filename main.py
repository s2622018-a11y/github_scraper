import os
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

# 1. 設定項目
# 課題要件: Googleが管理するリポジトリの一覧ページを指定
TARGET_URL = "[suspicious link removed]"
DB_PATH = os.path.join("db", "github_repos.db")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
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
    items = soup.select("li.Box-row")
    repositories = []

    for item in items:
        # ① リポジトリ名の取得
        repo_link = item.select_one("h3 a") or item.select_one("a[href*='/']")
        if repo_link is None:
            continue

        name = repo_link.get_text(" ", strip=True) or "Unknown"
        
        # ② 言語の取得
        language_elem = item.select_one('[itemprop="programmingLanguage"]')
        language = language_elem.get_text(" ", strip=True) if language_elem else "N/A"

        # ③ Starsの取得
        star_elem = item.select_one('a[href*="/stargazers"]')
        stars = star_elem.get_text(" ", strip=True) if star_elem else "0"

        repositories.append((name, language, stars))

    return repositories


def save_repositories(repositories):
    prepare_db_path()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                language TEXT,
                stars TEXT
            )
            """
        )
        cursor.execute("DELETE FROM repositories")

        for name, language, stars in repositories:
            cursor.execute(
                "INSERT INTO repositories (name, language, stars) VALUES (?, ?, ?)",
                (name, language, stars),
            )

        conn.commit()

# 課題要件: SELECT文を使って保存データを取得・画面表示する
        print("=== SQLite保存データ (SELECT文実行結果) ===")
        cursor.execute("SELECT id, name, language, stars FROM repositories")
        for row in cursor.fetchall():
            print(f"ID: {row[0]} | リポジトリ名: {row[1]} | 言語: {row[2]} | Stars: {row[3]}")


def main():
    try:
        soup = fetch_repository_page(TARGET_URL)
    except requests.RequestException as exc:
        print(f"Web fetch failed: {exc}. Continuing with an empty dataset.")
        soup = BeautifulSoup("", "html.parser")

    repositories = extract_repository_data(soup)
    save_repositories(repositories)


if __name__ == "__main__":
    main()
