from geoip2.errors import AddressNotFoundError
from user_agents import parse
from django.contrib.gis.geoip2 import GeoIP2


def get_ip(request):
    """Returns the IP of the request, accounting for the possibility of being
    behind a proxy.
    """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", None)
    if ip:
        # X_FORWARDED_FOR returns client1, proxy1, proxy2,...
        ip = ip.split(", ")[0]
    else:
        ip = request.META.get("REMOTE_ADDR", "")

    return ip


def get_user_agent(request):
    ua_string = request.META.get("HTTP_USER_AGENT", "Unknown-device")
    user_agent = parse(ua_string)
    return user_agent


def get_location(request):

    g = GeoIP2()
    try:
        req_info = g.city(get_ip(request))
        result = '{}, {}'.format(req_info['city'], req_info['country_name'])
    except (AddressNotFoundError, AttributeError):
        result = 'Unknown-IP-Location'

    return result


