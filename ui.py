import flet as ft
from packages import fetch_packages_from_website_async, filter_packages_by_query, all_packages, get_installed_packages, installed_packages, is_pacstall_installed

async def build_ui(page: ft.Page):
    """
    Builds the user interface for the Pacstall Package Browser.
    """
    page.title = "Pacstall GUI Manager."
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 800
    page.window_height = 600
    page.window_min_width = 600
    page.window_min_height = 400

    # Theme
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap"
    }
    page.theme = ft.Theme(font_family="Inter")

    def display_packages(packages_to_display):
        package_list_view.controls.clear()
        
        if packages_to_display:
            for pkg in packages_to_display:
                is_installed = pkg.get('name') in installed_packages
                visible_name = pkg.get("visibleName") or pkg.get("name")
                description = pkg.get("description") or "No description available"
                maintainer_text = (
                    f"Maintainer: {pkg['maintainer'][0]['name']}"
                    if pkg.get("maintainer") and len(pkg["maintainer"]) > 0
                    else "Maintainer: Unknown"
                )
                version = pkg.get("version", "N/A")
                pkg_type = pkg.get("type", "Unknown")

                package_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(visible_name, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                                ft.Text("Installed", color=ft.Colors.GREEN_600, weight=ft.FontWeight.BOLD, visible=is_installed)
                            ]),
                            ft.Text(f"Version: {version} • Type: {pkg_type}", size=11, color=ft.Colors.BLUE_GREY_600),
                            ft.Text(description, size=12, color=ft.Colors.BLUE_GREY_700),
                            ft.Text(maintainer_text, size=11, italic=True, color=ft.Colors.GREY_600),
                        ]),
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        border_radius=ft.border_radius.all(6),
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(1, ft.Colors.GREEN_200 if is_installed else ft.Colors.BLUE_GREY_100),
                        shadow=ft.BoxShadow(
                            spread_radius=0.5,
                            blur_radius=2,
                            color=ft.Colors.BLUE_GREY_50,
                            offset=ft.Offset(0, 1),
                        ),
                        on_click=lambda e, url=pkg["packageDetailsUrl"]: page.launch_url(url)
                    )
                )
        else:
            package_list_view.controls.append(
                ft.Text(
                    "No packages found matching your query.",
                    color=ft.Colors.GREY_500,
                    text_align=ft.TextAlign.CENTER
                )
            )

        page.update()

    async def load_and_display_packages(_=None):
        global all_packages, installed_packages

        pacstall_status.value = "Pacstall: Checking..."
        pacstall_status.color = ft.Colors.BLUE_GREY_400
        page.update()

        if is_pacstall_installed():
            pacstall_status.value = "Pacstall: Installed"
            pacstall_status.color = ft.Colors.GREEN_600
        else:
            pacstall_status.value = "Pacstall: Not Found"
            pacstall_status.color = ft.Colors.RED_600

        package_list_view.controls.clear()
        package_list_view.controls.append(
            ft.Text("Fetching all packages... This may take a moment.", color=ft.Colors.BLUE_600, text_align=ft.TextAlign.CENTER)
        )
        loading_indicator.visible = True
        search_input.disabled = True
        refresh_button.disabled = True
        page.update()

        installed_packages.clear()
        installed_packages.update(get_installed_packages())

        fetched_packages = await fetch_packages_from_website_async()
        all_packages[:] = sorted(fetched_packages, key=lambda x: x["name"].lower())

        loading_indicator.visible = False
        search_input.disabled = False
        refresh_button.disabled = False
        page.update()

        if all_packages:
            display_packages(all_packages)
        else:
            package_list_view.controls.clear()
            package_list_view.controls.append(
                ft.Text(
                    "Could not fetch packages from pacstall.dev. "
                    "Please check your internet connection or try again later.",
                    color=ft.Colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                )
            )
            page.update()

    def filter_and_display_packages(e):
        query = e.control.value
        if not all_packages:
            package_list_view.controls.clear()
            package_list_view.controls.append(
                ft.Text("No packages loaded yet. Click 'Refresh' to load them.", color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
            )
            page.update()
            return

        filtered = filter_packages_by_query(query)
        display_packages(filtered)

    pacstall_status = ft.Text("", size=12, weight=ft.FontWeight.BOLD)

    search_input = ft.TextField(
        label="Search packages...",
        hint_text="e.g., linux-kernel, brave-browser",
        expand=True,
        border_radius=ft.border_radius.all(8),
        border_color=ft.Colors.BLUE_GREY_200,
        focused_border_color=ft.Colors.BLUE_500,
        on_change=filter_and_display_packages,
        on_submit=filter_and_display_packages,
        text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900)
    )
    
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Refresh package list from database",
        icon_color=ft.Colors.BLUE_600,
        on_click=load_and_display_packages,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            overlay_color=ft.Colors.BLUE_50
        )
    )

    loading_indicator = ft.ProgressBar(
        width=400, 
        visible=True,
        color=ft.Colors.BLUE_600,
        bgcolor=ft.Colors.BLUE_100
    )

    package_list_view = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.padding.all(16),
        auto_scroll=False,
    )
    
    results_container = ft.Container(
        content=package_list_view,
        expand=True,
        padding=ft.padding.all(10),
        border_radius=ft.border_radius.all(12),
        bgcolor=ft.Colors.BLUE_GREY_50,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=10,
            color=ft.Colors.BLUE_GREY_100,
            offset=ft.Offset(0, 5),
        ),
    )

    page.add(
        ft.Column(
            [
                ft.Container(
                    content=ft.Row([
                        ft.Text(
                            "Pacstall Package Browser",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_900,
                        ),
                        pacstall_status
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(bottom=20)
                ),
                ft.Row(
                    [search_input, refresh_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                ft.Container(
                    content=loading_indicator,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10)
                ),
                results_container
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )
    )

    page.on_ready = await load_and_display_packages()
