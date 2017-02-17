from django.shortcuts import render_to_response
from django.template import RequestContext

class FacebookFakeRootMiddleware(object):
    def process_response(self, request, response):
        ua = request.META.get('HTTP_USER_AGENT')
        if ua and "facebookexternalhit" in ua:
            return render_to_response("index.html", context_instance=RequestContext(request, {}))
        else:
            return response