import flet as ft


def main(page: ft.Page):
    page.title = "GIF Test"
    page.bgcolor = "#000000"
    
    gif = ft.Image(
        src="aiback_small.gif",
        width=400,
        height=400,
        fit=ft.BoxFit.COVER,
    )
    
    page.add(
        ft.Text("GIF Test", size=30, color="#FFFFFF"),
        gif,
    )


ft.run(main, assets_dir="assets")