import flet as ft
from app import build_ui

async def main(page: ft.Page):
    await build_ui(page)

if __name__ == "__main__":
    ft.app(target=main)
