def site(request):
    site_url = request.META.get('HTTP_HOST','').lower()
    return {
        'SITE_URL': site_url,
    }