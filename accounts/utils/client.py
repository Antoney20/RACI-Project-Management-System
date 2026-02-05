from django.utils.encoding import force_str

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_agent(request):
    return force_str(request.META.get('HTTP_USER_AGENT', ''))


def parse_user_agent(user_agent):
    """
    Very light parsing.
    You can later replace this with 'user-agents' lib if needed.
    """
    ua = user_agent.lower()

    browser = 'Unknown'
    os = 'Unknown'

    if 'chrome' in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'

    if 'windows' in ua:
        os = 'Windows'
    elif 'mac' in ua:
        os = 'macOS'
    elif 'linux' in ua:
        os = 'Linux'
    elif 'android' in ua:
        os = 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        os = 'iOS'

    return browser, os


def detect_device_type(user_agent: str) -> str:
    ua = user_agent.lower()

    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobile'
    if 'ipad' in ua or 'tablet' in ua:
        return 'tablet'
    return 'desktop'