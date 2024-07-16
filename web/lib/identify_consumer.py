from django.http import HttpRequest


# Used by APITALLY to identify the user for analytics
def identify_consumer(request: HttpRequest) -> str | None:
    if request.user.is_authenticated:
        return request.user.username
    return None
