import requests

headers = {
    "Host": "irena1.intercity.pl",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Sec-GPC": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Connection": "keep-alive",
}


def start_session(username, password) -> requests.Session:
    session = requests.Session()
    session.headers.update(headers)

    url = "https://irena1.intercity.pl/mbweb/main/matter/desktop/main-menu"
    response = session.get(url)
    response.raise_for_status()

    data = {
        "j_username": username.lower().strip(),
        "j_password": password.strip(),
    }
    response = session.post(
        url="https://irena1.intercity.pl/mbweb/j_security_check", data=data
    )
    response.raise_for_status()

    if response.request.path_url == "/mbweb/login?login-status=failed":
        raise Exception("Authentication failed")

    return session
