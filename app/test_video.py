import flet as ft
import flet_video as fv


def main(page: ft.Page):
    page.title = "Video Test"
    page.bgcolor = "#000000"
    
    video = fv.Video(
        playlist=[fv.VideoMedia("aiback.mp4")],
        autoplay=True,
        playlist_mode=fv.PlaylistMode.LOOP,
        muted=True,
        width=500,
        height=500,
        fit=ft.BoxFit.COVER,
    )
    
    page.add(
        ft.Text("Video Test", size=30, color="#FFFFFF"),
        video,
    )


ft.run(main, assets_dir="assets")