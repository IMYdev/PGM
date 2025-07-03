import aiohttp
import subprocess

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
