import aiohttp
import subprocess
import asyncio

all_packages = []
installed_packages = set()

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