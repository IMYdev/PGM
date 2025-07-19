import os
import re
import json
import signal
import asyncio
import datetime
import subprocess

import aiohttp
import flet as ft


all_packages = []
installed_packages = set()
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".PGM")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config")

def is_pacstall_installed():
    """
    Checks if Pacstall is installed and available in the system's PATH.
    """
    try:
        subprocess.run(['pacstall', '--version'], capture_output=True, text=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def get_installed_packages():
    """
    Gets a set of all installed Pacstall packages.
    """
    try:
        # Run the pacstall command to list installed packages
        result = subprocess.run(['pacstall', '-L'], capture_output=True, text=True, check=True)
        
        # Process the output to extract package names
        lines = result.stdout.strip().split('\n')
        
        # The first line is a header, so we skip it
        # Each subsequent line should be a package name
        installed = {line.strip() for line in lines[1:]}
        return installed
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return set()

async def fetch_packages_from_website_async():
    """
    Asynchronously fetch package data from Pacstall API.
    """
    url = "https://pacstall.dev/api/repology"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    print(f"HTTP Error: {response.status}")
                    return []

                data = await response.json()
                return data  # Returns the full list of package dicts

    except aiohttp.ClientError as e:
        print(f"AIOHTTP Error fetching packages: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def filter_packages_by_query(query: str):
    """
    Filters the globally stored packages based on the search query.
    """
    if not all_packages:
        return []
    
    return [pkg for pkg in all_packages if query.lower() in pkg["name"].lower()]

async def fetch_package_details(package_name: str):
    """
    Fetch detailed info for a single package by name from the API.
    """
    url = f"https://pacstall.dev/api/packages/{package_name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    print(f"HTTP Error fetching details for {package_name}: {response.status}")
                    return None
                return await response.json()
    except Exception as e:
        print(f"Error fetching package details for {package_name}: {e}")
        return None

async def install_package(package_name: str, password: str = None):
    """
    Installs a Pacstall package asynchronously.
    If password is provided, uses sudo for installation.
    Returns (success: bool, output: str)
    """
    try:
        if password is not None:
            proc = await asyncio.create_subprocess_exec(
                'sudo', '-S', 'pacstall', '-I', package_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            # Send password
            stdout, _ = await proc.communicate((password + '\n').encode())
        else:
            proc = await asyncio.create_subprocess_exec(
                'pacstall', '-I', package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await proc.communicate()

        output = stdout.decode(errors='ignore')
        success = proc.returncode == 0
        if success:
            installed_packages.clear()
            installed_packages.update(get_installed_packages())
        return success, output
    except Exception as e:
        return False, str(e)

async def uninstall_package(package_name: str, password: str = None):
    """
    Uninstalls a Pacstall package asynchronously.
    If password is provided, uses sudo for uninstallation.
    Returns (success: bool, output: str)
    """
    try:
        if password is not None:
            proc = await asyncio.create_subprocess_exec(
                'sudo', '-S', 'pacstall', '-R', package_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            # Send password
            stdout, _ = await proc.communicate((password + '\n').encode())
        else:
            proc = await asyncio.create_subprocess_exec(
                'pacstall', '-R', package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await proc.communicate()

        output = stdout.decode(errors='ignore')
        success = proc.returncode == 0
        if success:
            installed_packages.clear()
            installed_packages.update(get_installed_packages())
        return success, output
    except Exception as e:
        return False, str(e)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

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

    config = load_config()
    theme_value = config.get("theme", "light").lower()
    page.theme_mode = ft.ThemeMode.DARK if theme_value == "dark" else ft.ThemeMode.LIGHT

    def toggle_theme(e):
        new_mode = (
            ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        )
        page.theme_mode = new_mode
        theme_toggle.icon = (
            ft.Icons.DARK_MODE if new_mode == ft.ThemeMode.DARK else ft.Icons.LIGHT_MODE
        )
        save_config({"theme": "dark" if new_mode == ft.ThemeMode.DARK else "light"})
        page.update()

    theme_toggle = ft.IconButton(
        icon=ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.LIGHT_MODE,
        tooltip="Toggle Theme",
        on_click=toggle_theme,
    )


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
        content=details_container
    )
    page.overlay.append(package_details_dialog)

    sudo_password_field = ft.TextField(
        label="Sudo Password",
        password=True,
        can_reveal_password=True,
        autofocus=True,
        width=300
    )

    password_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Authentication Required"),
        content=sudo_password_field,
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: close_password_dialog()),
            ft.ElevatedButton("Continue", on_click=lambda e: on_password_submit())
        ]
    )

    page.overlay.append(password_dialog)

    about_button = ft.IconButton(
        icon=ft.Icons.INFO,
        on_click=lambda e: show_about_section())
    
    about_section = ft.AlertDialog(
        modal=False,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Image(
                        src="PGM.svg",
                        width=page.width / 10,
                        fit=ft.ImageFit.CONTAIN
                    ),
                    alignment=ft.alignment.top_center,
                ),
                ft.Text("Pacstall GUI Manager by IMYdev.", size=page.width / 60), # This scaling is cursed but it works (:
                ft.TextButton(text="Developer website", on_click=lambda e: page.launch_url("https://imy.com.ly")),
                ft.TextButton(text="Project page", on_click=lambda e: page.launch_url("https://github.com/IMYdev/PGM")),
                ft.Row(
                    controls= [
                        ft.Text("Logo by:"),
                        ft.TextButton(text="@april865", on_click=lambda e: page.launch_url("https://t.me/april865"))
                    ],
                    tight=True
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            tight=True
        )
    )


    page.overlay.append(about_section)


    def on_resize():
        details_container.width = page.width / 2
        details_container.update()

    page.on_resize = on_resize

    def close_package_dialog():
        package_details_dialog.open = False
        details_column.controls.clear()
        page.update()

    def close_password_dialog():
        password_dialog.open = False
        sudo_password_field.value = ""
        page.update()

    def close_dialog(dialog):
        dialog.open = False
        page.update()
    
    def show_about_section():
        about_section.open = True
        page.update()


    loop = asyncio.get_running_loop()
    
    def on_password_submit():
        package_name = password_dialog.data
        password = sudo_password_field.value + "\n"
        password_dialog.open = False
        sudo_password_field.value = ""
        page.update()

        # Create a new un/install-specific dialog
        log_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
        log_column.auto_scroll = True

        log_view = ft.Container(
            content=log_column,
            width=page.width * 0.75,
            height=400,
            padding=10,
            bgcolor=ft.Colors.BLACK,
            border_radius=ft.border_radius.all(8),
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

        uninstall_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Uninstalling {package_name}..."),
            content=log_view,
            actions=[ft.TextButton("Cancel", on_click=lambda e: cancel_process(uninstall_dialog))]
        )

        install_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Installing {package_name}..."),
            content=log_view,
            actions=[ft.TextButton("Cancel", on_click=lambda e: cancel_process(install_dialog))]
        )

        if package_name in installed_packages:
            page.overlay.append(uninstall_dialog)
            uninstall_dialog.open = True
            page.update()
            asyncio.run_coroutine_threadsafe(
                uninstall_and_show_output(package_name, password, log_column, uninstall_dialog),
                loop
            )

        if package_name not in installed_packages:
            page.overlay.append(install_dialog)
            install_dialog.open = True
            page.update()
            asyncio.run_coroutine_threadsafe(
                install_and_show_output(package_name, password, log_column, install_dialog),
                loop
        )


    
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

    def clean_log_line(line):
        # Remove ANSI escape codes and strip whitespace
        return ansi_escape.sub('', line).strip()
    
    running_processes = {}

    def cancel_process(dialog):
        proc = running_processes.get(dialog)
        if proc and proc.returncode is None:
            try:
                proc.send_signal(signal.SIGINT)
            except Exception as e:
                print(f"Failed to send SIGINT: {e}")
        close_dialog(dialog)
    
    async def install_and_show_output(package_name, password, log_column, dialog):
        try:
            log_column.controls.append(ft.Text("Starting installation...", color=ft.Colors.BLUE_200))
            dialog.update()
            # Start install and keep process reference
            proc = await asyncio.create_subprocess_exec(
                'sudo', '-S', 'pacstall', '-I', package_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            ) if password else await asyncio.create_subprocess_exec(
                'pacstall', '-I', package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            running_processes[dialog] = proc
            if password:
                stdout, _ = await proc.communicate((password + '\n').encode())
            else:
                stdout, _ = await proc.communicate()
            output = stdout.decode(errors='ignore')
            for line in output.splitlines():
                clean_line = clean_log_line(line)
                if clean_line:
                    log_column.controls.append(
                        ft.Text(clean_line, color=ft.Colors.GREEN_100, size=12)
                    )
                    dialog.update()
            success = proc.returncode == 0
            if success:
                installed_packages.clear()
                installed_packages.update(get_installed_packages())
                display_packages(all_packages, installed_only=viewing_installed)
                log_column.controls.append(ft.Text("Install complete.", color=ft.Colors.GREEN_400))
            else:
                log_column.controls.append(ft.Text("Install failed.", color=ft.Colors.RED_400))
            dialog.actions = [ft.TextButton("Close", on_click=lambda e: close_dialog(dialog))]
            dialog.update()
        except Exception as e:
            log_column.controls.append(ft.Text(f"Error: {e}", color=ft.Colors.RED_400))
            dialog.update()
        finally:
            running_processes.pop(dialog, None)

    async def uninstall_and_show_output(package_name, password, log_column, dialog):
        try:
            log_column.controls.append(ft.Text("Starting uninstall...", color=ft.Colors.BLUE_200))
            dialog.update()
            proc = await asyncio.create_subprocess_exec(
                'sudo', '-S', 'pacstall', '-R', package_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            ) if password else await asyncio.create_subprocess_exec(
                'pacstall', '-R', package_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            running_processes[dialog] = proc
            if password:
                stdout, _ = await proc.communicate((password + '\n').encode())
            else:
                stdout, _ = await proc.communicate()
            output = stdout.decode(errors='ignore')
            for line in output.splitlines():
                clean_line = clean_log_line(line)
                if clean_line:
                    log_column.controls.append(
                        ft.Text(clean_line, color=ft.Colors.GREEN_100, size=12)
                    )
                    dialog.update()
            success = proc.returncode == 0
            if success:
                installed_packages.clear()
                installed_packages.update(get_installed_packages())
                display_packages(all_packages, installed_only=viewing_installed)
                log_column.controls.append(ft.Text("Uninstall complete.", color=ft.Colors.GREEN_400))
            else:
                log_column.controls.append(ft.Text("Uninstall failed.", color=ft.Colors.RED_400))
            dialog.actions = [ft.TextButton("Close", on_click=lambda e: close_dialog(dialog))]
            dialog.update()
        except Exception as e:
            log_column.controls.append(ft.Text(f"Error: {e}", color=ft.Colors.RED_400))
            dialog.update()
        finally:
            running_processes.pop(dialog, None)



    async def on_package_click(e, package_name):
        details_column.controls.clear()
        package_details_dialog.title.value = f"Loading..."
        package_details_dialog.open = True
        package_details_dialog.actions = [ft.Text("Please wait...")]  # placeholder
        page.update()

        details = await fetch_package_details(package_name)
        if not details:
            package_details_dialog.title.value = "Error"
            details_column.controls.append(
                ft.Text("Failed to fetch package details.")
            )
            package_details_dialog.actions = [
            ft.TextButton("Close", on_click=lambda e: close_package_dialog())
            ]
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
        
        # Uninstall button logic
        actions = []
        if package_name in installed_packages:
            def on_uninstall_click(e):

                password_dialog.data = package_name
                sudo_password_field.value = ""
                password_dialog.open = True
                page.update()

            uninstall_btn = ft.ElevatedButton(
                text="Uninstall",
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600,
                on_click=on_uninstall_click
            )
            actions.append(uninstall_btn)
        if package_name not in installed_packages:
            def on_install_click(e):

                password_dialog.data = package_name
                sudo_password_field.value = ""
                password_dialog.open = True
                page.update()


            install_btn = ft.ElevatedButton(
                text="Install",
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600,
                on_click=on_install_click
            )
            actions.append(install_btn)


        actions.append(ft.TextButton("Close", on_click=lambda e: close_package_dialog()))
        package_details_dialog.actions = actions


        details_column.controls.extend(content_list)
        page.update()

    # Inital state of list view
    viewing_installed = False

    def display_packages(packages_to_display, installed_only=False):
        package_list_view.controls.clear()

        filtered = [pkg for pkg in packages_to_display if pkg.get('name') in installed_packages] if installed_only else packages_to_display

        if filtered:
            for pkg in filtered:
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
                                ft.Text(visible_name, weight=ft.FontWeight.BOLD, color=ft.ColorScheme.primary),
                                ft.Text("Installed", color=ft.Colors.GREEN_600, weight=ft.FontWeight.BOLD, visible=is_installed)
                            ]),
                            ft.Text(f"Version: {version} • Type: {pkg_type}", size=11, color=ft.ColorScheme.primary),
                            ft.Text(description, size=12, color=ft.ColorScheme.primary),
                            ft.Text(maintainer_text, size=11, italic=True, color=ft.ColorScheme.primary),
                        ]),
                        padding=ft.padding.symmetric(vertical=8, horizontal=12),
                        border_radius=ft.border_radius.all(6),
                        bgcolor=ft.ColorScheme.surface,
                        border=ft.border.all(1, ft.Colors.GREEN_200 if is_installed else ft.Colors.BLUE_GREY_100),
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

    switch_button = ft.ElevatedButton(
    text="Show Installed Packages",
    on_click=lambda e: toggle_package_view(),
    style=ft.ButtonStyle(padding=ft.padding.symmetric(vertical=10, horizontal=14))
)
    def toggle_package_view(e):
        global viewing_installed
        viewing_installed = not viewing_installed
        switch_button.text = "Show All Packages" if viewing_installed else "Show Installed Packages"
        switch_button.update()
        display_packages(all_packages, installed_only=viewing_installed)

    switch_button.on_click = toggle_package_view

    async def load_and_display_packages(_=None):
        global all_packages, installed_packages, viewing_installed

        # Reset view state
        viewing_installed = False

        # Update UI immediately
        switch_button.text = "Show Installed Packages"
        switch_button.update()

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
        switch_button.disabled = True
        page.update()

        installed_packages.clear()
        installed_packages.update(get_installed_packages())

        fetched_packages = await fetch_packages_from_website_async()
        all_packages[:] = sorted(fetched_packages, key=lambda x: x["name"].lower())

        loading_indicator.visible = False
        search_input.disabled = False
        refresh_button.disabled = False
        switch_button.disabled = False
        page.update()

        if all_packages:
            display_packages(all_packages, installed_only=viewing_installed)
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
        display_packages(filtered, installed_only=viewing_installed)

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
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
    )

    page.add(
        ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(  # Title + About
                                [
                                    ft.Text(
                                        "Pacstall GUI Manager",
                                        size=28,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.PRIMARY
                                    ),
                                    about_button
                                ],
                                spacing=10,
                                alignment=ft.MainAxisAlignment.START,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            ft.Column(  # Status + Theme toggle
                                [
                                    ft.Container(pacstall_status, alignment=ft.alignment.center),
                                    theme_toggle
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(bottom=20)
                ),

                ft.Row(
                    [search_input, refresh_button, switch_button],
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
