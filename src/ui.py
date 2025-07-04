import flet as ft
from packages import fetch_packages_from_website_async, filter_packages_by_query, all_packages, get_installed_packages, installed_packages, is_pacstall_installed, fetch_package_details
import datetime

def format_date(iso_date_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_date_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_date_str

async def build_ui(page: ft.Page):
    page.title = "Pacstall GUI Manager."
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 800
    page.window_height = 600
    page.window_min_width = 600
    page.window_min_height = 400

    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap"
    }
    page.theme = ft.Theme(font_family="Inter")

    details_column = ft.Column([], scroll=ft.ScrollMode.AUTO)

    details_container = ft.Container(
        content=details_column,
        width=page.width / 2,
        padding=10,
    )

    package_details_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Package Details"),
        content=details_container,
        actions=[ft.TextButton("Close", on_click=lambda e: close_package_dialog())]
    )
    page.overlay.append(package_details_dialog)

    def on_resize(e):
        details_container.width = page.width / 2
        details_container.update()

    page.on_resize = on_resize

    def close_package_dialog():
        package_details_dialog.open = False
        details_column.controls.clear()
        page.update()

    async def on_package_click(e, package_name):
        details_column.controls.clear()
        package_details_dialog.title.value = f"Loading..."
        package_details_dialog.open = True
        page.update()

        details = await fetch_package_details(package_name)
        if not details:
            package_details_dialog.title.value = "Error"
            details_column.controls.append(
                ft.Text("Failed to fetch package details.")
            )
            page.update()
            return

        package_details_dialog.title.value = "Package Details"
        content_list = []

        content_list.append(ft.Text(f"Name: {details.get('prettyName', package_name)}", weight=ft.FontWeight.BOLD, size=18))
        content_list.append(ft.Text(f"Version: {details.get('version', 'N/A')}", italic=True))

        homepage = details.get("homepage")
        if homepage:
            content_list.append(
                ft.Row([
                    ft.Text("Homepage: "),
                    ft.TextButton(homepage, on_click=lambda e, url=homepage: page.launch_url(url))
                ])
            )

        description = details.get("description")
        if description:
            content_list.append(ft.Text(description))

        maintainers = details.get("maintainers") or []
        if maintainers:
            content_list.append(ft.Text("Maintainers:", weight=ft.FontWeight.BOLD))
            for m in maintainers:
                content_list.append(ft.Text(m))

        architectures = details.get("architectures") or []
        if architectures:
            content_list.append(ft.Text(f"Architectures: {', '.join(architectures)}"))

        licenses = details.get("license") or []
        if licenses:
            content_list.append(ft.Text(f"License: {', '.join(licenses)}"))

        # Runtime dependencies
        runtime_dependencies = details.get("runtimeDependencies") or []

        if runtime_dependencies:
            content_list.append(ft.Text("Runtime Dependencies:", weight=ft.FontWeight.BOLD))

            runtime_table = ft.Row(
                scroll=ft.ScrollMode.AUTO,
                expand=False,
                width=details_container.width,
                spacing=6,
                controls=[]
            )

            for dep in runtime_dependencies:
                value = dep.get("value", "Unknown")
                arch = dep.get("arch", "amd64")
                text = f"{arch}: {value}"

                runtime_table.controls.append(
                    ft.Container(
                        content=ft.Text(
                            text,
                            selectable=True,
                            size=12,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        padding=ft.padding.symmetric(vertical=4, horizontal=10),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=ft.border_radius.all(6),
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        tooltip="Dependency"
                    )
                )

            content_list.append(runtime_table)
        else:
            content_list.append(ft.Text("Runtime Dependencies: None"))




        # Optional dependencies
        optional_deps = details.get("optionalDependencies") or []

        is_visible = False

        def vis(e=None):
            nonlocal is_visible, opt_table
            is_visible = not is_visible
            vis_button.text = "Hide" if is_visible else "Show"
            opt_table.visible = is_visible
            vis_button.update()
            opt_table.update()

        vis_button = ft.ElevatedButton(text="Show", on_click=vis)

        if optional_deps:
            content_list.append(ft.Text("Optional Dependencies:", weight=ft.FontWeight.BOLD))
            content_list.append(vis_button)

            opt_table = ft.Row(
                scroll=ft.ScrollMode.AUTO,
                expand=False,
                width=details_container.width,
                spacing=6,
                visible=is_visible,
                controls=[]
            )

            for dep in optional_deps:
                value = dep.get("value", "Unknown")
                arch = dep.get("arch", "amd64")
                text = f"{arch}: {value}"

                opt_table.controls.append(
                    ft.Container(
                        content=ft.Text(
                            text,
                            selectable=True,
                            size=12,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        padding=ft.padding.symmetric(vertical=4, horizontal=10),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=ft.border_radius.all(6),
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        tooltip="Optional dependency"
                    )
                )

            content_list.append(opt_table)



        # Build dependencies
        build_deps = details.get("buildDependencies") or []

        build_visible = False

        def toggle_build(e=None):
            nonlocal build_visible, build_table
            build_visible = not build_visible
            build_button.text = "Hide" if build_visible else "Show"
            build_table.visible = build_visible
            build_button.update()
            build_table.update()

        build_button = ft.ElevatedButton(text="Show", on_click=toggle_build)

        if build_deps:
            content_list.append(ft.Text("Build Dependencies:", weight=ft.FontWeight.BOLD))
            content_list.append(build_button)

            build_table = ft.Row(
                scroll=ft.ScrollMode.AUTO,
                expand=False,
                width=details_container.width,
                spacing=6,
                visible=build_visible,
                controls=[]
            )

            for dep in build_deps:
                value = dep.get("value", "Unknown")
                arch = dep.get("arch", "amd64")
                text = f"{arch}: {value}"

                build_table.controls.append(
                    ft.Container(
                        content=ft.Text(
                            text,
                            selectable=True,
                            size=12,
                            color=ft.Colors.BLUE_GREY_800,
                        ),
                        padding=ft.padding.symmetric(vertical=4, horizontal=10),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=ft.border_radius.all(6),
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        tooltip="Build dependency"
                    )
                )

            content_list.append(build_table)


        # Conflicted packages
        conflicts = details.get("conflicts") or []
        if conflicts:
            content_list.append(ft.Text("Conflicts:", weight=ft.FontWeight.BOLD))

            conf_view = ft.Row(
                scroll=ft.ScrollMode.AUTO,
                expand=False,
                height=35,
                width=350,
                spacing=1,
                controls=[
                    ft.Container(
                        content=ft.Text(
                            conf.get("value", "Unknown"),
                            selectable=True,
                            color=ft.Colors.BLUE_GREY_800,
                            size=12,
                        ),
                        padding=ft.padding.symmetric(vertical=6, horizontal=10),
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border_radius=ft.border_radius.all(6),
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    )
                    for conf in conflicts
                ]
            )

            content_list.append(conf_view)
        else:
            content_list.append(ft.Text(f"Conflicts: None"))

        last_updated = details.get("lastUpdatedAt")
        if last_updated:
            content_list.append(ft.Text(f"Last Updated: {format_date(last_updated)}"))

        # Source URLs
        sources = details.get("source") or []
        if sources:
            content_list.append(ft.Text("Source URLs:", weight=ft.FontWeight.BOLD))

            sources_view = ft.Container(
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    spacing=4,
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                f"{s.get('arch')}: {s.get('value')}" if s.get("arch") else s.get("value"),
                                selectable=True,
                                color=ft.Colors.BLUE_700,
                                size=14,
                            ),
                            padding=ft.padding.symmetric(vertical=6, horizontal=10),
                            bgcolor=ft.Colors.BLUE_GREY_50,
                            border_radius=ft.border_radius.all(6),
                            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        )
                        for s in sources
                    ]
                ),
                expand=True,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border_radius=ft.border_radius.all(8),
                padding=ft.padding.all(4),
            )

            content_list.append(sources_view)

        details_column.controls.extend(content_list)
        page.update()

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

                def make_click_handler(name):
                    async def handler(e):
                        await on_package_click(e, name)
                    return handler

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
                        on_click=make_click_handler(pkg["name"])
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
                            "Pacstall GUI Manager",
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
