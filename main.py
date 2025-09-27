import flet as ft
import json
import os
from datetime import datetime
from atproto import Client, models

DATA_FILE = "data.json"
ACCOUNTS_FILE = "accounts.json"


# --- ヘルパー ---
def load_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_message(text, image):
    entry = {
        "text": text,
        "image": image,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data = load_history()
    data.append(entry)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)


# --- エラーメッセージ表示 ---
def show_error(page: ft.Page, message: str, color="red"):
    page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color, open=True)
    page.update()


# --- グローバル変数的に扱う ---
login_label = None  # ホーム画面のログイン状態ラベル用


def login_with_account(account, page: ft.Page, main_view_func):
    try:
        client = Client()
        client.login(account["handle"], account["password"])
        page.session.set("current_account", account)

        # ログイン状態ラベルを更新
        global login_label
        if login_label:
            login_label.value = f"ログイン中: {account['name']}"
            login_label.color = "green"

        page.snack_bar = ft.SnackBar(ft.Text(f"{account['name']} でログイン"))
        page.snack_bar.open = True

        # ホーム画面に戻す
        page.views.clear()
        page.views.append(main_view_func(page))
    except Exception as e:
        page.snack_bar = ft.SnackBar(ft.Text(f"ログイン失敗: {e}"), bgcolor="red")
        page.snack_bar.open = True
    page.update()


# --- メイン ---
def main(page: ft.Page):
    page.title = "Flet Bluesky Poster"
    page.window_width = 700
    page.window_height = 800
    page.padding = 20
    page.spacing = 20
    page.theme_mode = "light"

    # 投稿画面共通
    text_input = ft.TextField(
        label="投稿内容",
        multiline=True,
        expand=True,
        min_lines=4,
        max_lines=8,
        border_radius=10,
    )
    image_path = ft.TextField(label="選択された画像", read_only=True, expand=True)
    messages = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    # 投稿履歴ロード
    def load_messages_into_list():
        messages.controls.clear()
        for item in reversed(load_history()):
            messages.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(item["timestamp"], size=12, color="grey"),
                                ft.Text(item["text"], size=14, weight="w500"),
                                ft.Text(
                                    f"画像: {item['image']}",
                                    size=12,
                                    italic=True,
                                    color="blue",
                                ),
                            ]
                        ),
                        padding=10,
                    )
                )
            )

    # テーマ切替
    def toggle_theme(e):
        page.theme_mode = "light" if page.theme_mode == "dark" else "dark"
        theme_btn.icon = (
            ft.Icons.DARK_MODE if page.theme_mode == "dark" else ft.Icons.WB_SUNNY
        )
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.WB_SUNNY, tooltip="テーマ切替", on_click=toggle_theme
    )

    # アカウント管理ボタン
    def go_to_accounts(e):
        page.go("/accounts")

    round_btn = ft.IconButton(
        icon=ft.Icons.SUPERVISED_USER_CIRCLE,
        tooltip="アカウント管理",
        on_click=go_to_accounts,
    )

    # ファイルピッカー
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            if not f.name.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                show_error(page, "画像ファイルを選んでください")
                return
            image_path.value = f.path
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)
    pick_button = ft.ElevatedButton(
        "画像を選択", on_click=lambda e: file_picker.pick_files(allow_multiple=False)
    )

    # 投稿ボタン
    def send_click(e):
        global login_label  # 関数の一番最初に書く
        account = page.session.get("current_account")

        if not account:
            if login_label:
                login_label.value = "未ログイン: 投稿できません"
                login_label.color = "red"
            page.snack_bar = ft.SnackBar(
                ft.Text("アカウントでログインしてください"), bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()
            return

        if not text_input.value.strip() and not image_path.value.strip():
            page.snack_bar = ft.SnackBar(
                ft.Text("投稿内容または画像を入力してください"), bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()
            return

        # 投稿処理
        save_message(text_input.value, image_path.value)
        messages.controls.insert(
            0,
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                size=12,
                                color="grey",
                            ),
                            ft.Text(text_input.value, size=14, weight="w500"),
                            ft.Text(
                                f"画像: {image_path.value}",
                                size=12,
                                italic=True,
                                color="blue",
                            ),
                        ]
                    ),
                    padding=10,
                )
            ),
        )

        try:
            client = Client()
            client.login(account["handle"], account["password"])
            if image_path.value:
                with open(image_path.value, "rb") as f:
                    blob = client.com.atproto.repo.upload_blob(f)
                embed = models.AppBskyEmbedImages.Main(
                    images=[
                        models.AppBskyEmbedImages.Image(
                            alt=os.path.basename(image_path.value), image=blob.blob
                        )
                    ]
                )
                client.send_post(text_input.value, embed=embed)
            else:
                client.send_post(text_input.value)
        except Exception as ex:
            show_error(page, f"Bluesky投稿エラー: {ex}")

        # 投稿後はラベルをログイン状態に戻す
        if login_label and account:
            login_label.value = f"ログイン中: {account['name']}"
            login_label.color = "green"

        text_input.value = ""
        image_path.value = ""
        page.update()

    send_button = ft.ElevatedButton(
        "投稿する", on_click=send_click, bgcolor="green", color="white"
    )

    # --- ページビュー ---
    def view_main(page):
        global login_label

        current_account = page.session.get("current_account")
        if current_account:
            login_label = ft.Text(
                f"ログイン中: {current_account['name']}", color="green", size=14
            )
        else:
            login_label = ft.Text("未ログイン", color="red", size=14)

        header = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Bluesky 投稿アプリ", size=22, weight="bold", expand=True
                        ),
                        round_btn,
                        theme_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                login_label,
            ]
        )

        main_col = ft.Column(
            [
                header,
                ft.Divider(),
                ft.Row([pick_button, image_path], spacing=10),
                text_input,
                send_button,
                ft.Divider(),
                ft.Text("📜 投稿履歴", size=18, weight="bold"),
                messages,
            ],
            spacing=12,
            expand=True,
        )

        load_messages_into_list()
        return ft.View("/", [main_col])

    def view_accounts(page):
        name_input = ft.TextField(label="名前", width=300)
        handle_input = ft.TextField(label="Handle", width=300)
        pass_input = ft.TextField(
            label="Password", password=True, can_reveal_password=True, width=300
        )
        accounts_column = ft.Column(spacing=10)

        def refresh_accounts():
            accounts_column.controls.clear()
            accounts = load_accounts()
            for i, acc in enumerate(accounts):
                accounts_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(f"名前: {acc['name']}", weight="bold"),
                                    ft.Text(f"Handle: {acc['handle']}"),
                                    ft.Row(
                                        [
                                            ft.ElevatedButton(
                                                "切り替え",
                                                on_click=lambda e,
                                                a=acc: login_with_account(
                                                    a, page, view_main
                                                ),
                                            ),
                                            ft.ElevatedButton(
                                                "削除",
                                                bgcolor="red",
                                                color="white",
                                                on_click=lambda e,
                                                idx=i: delete_account(idx),
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            padding=10,
                        )
                    )
                )

        def delete_account(idx):
            accounts = load_accounts()
            accounts.pop(idx)
            save_accounts(accounts)
            refresh_accounts()
            page.update()

        refresh_accounts()

        def save_account(e):
            name = name_input.value.strip()
            handle = handle_input.value.strip()
            password = pass_input.value.strip()

            if not (name and handle and password):
                show_error(page, "すべての項目を入力してください")
                return

            accounts = load_accounts()
            accounts.append({"name": name, "handle": handle, "password": password})
            save_accounts(accounts)
            show_error(page, "アカウントを保存しました", color="green")
            refresh_accounts()
            page.update()

        back_btn = ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/"))

        return ft.View(
            "/accounts",
            [
                ft.AppBar(title=ft.Text("アカウント管理"), leading=back_btn),
                ft.Column(
                    [
                        name_input,
                        handle_input,
                        pass_input,
                        ft.ElevatedButton("保存", on_click=save_account),
                        ft.Text("保存済みアカウント", size=18, weight="bold"),
                        accounts_column,
                    ],
                    spacing=15,
                    scroll="adaptive",
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
        )

    # --- ルーティング ---
    def route_change(e):
        page.views.clear()
        if page.route in ("/", ""):
            page.views.append(view_main(page))
        elif page.route == "/accounts":
            page.views.append(view_accounts(page))
        page.update()

    page.on_route_change = route_change
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)
