# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.signals import user_logged_out
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from multiple_auth import (
    xlogin as auth_login,
    SESSION_KEY, LOGGED_USERS_KEY, USERS_PREFERENCES_KEY,
    store_user_preferences
)

def _form_valid(request, form, success_url):
    auth_login(request, form.get_user())
    return HttpResponseRedirect(success_url)

@csrf_protect
@never_cache
def switch(request, user_index, redirect_field_name=REDIRECT_FIELD_NAME):
    # Store current user session preferences 
    user_index = int(user_index)
    redirect_to = request.GET.get(redirect_field_name, settings.LOGIN_REDIRECT_URL)

    if len(request.session.get(LOGGED_USERS_KEY, [])) < (user_index + 1):
        return HttpResponseRedirect(redirect_to)

    # Get destination user preference and restore it
    store_user_preferences(request)

    # Set destination user to session
    user_session_data = request.session.get(LOGGED_USERS_KEY)[user_index]
    request.session.cycle_key()
    request.session.update(user_session_data)

    # Restore user preferences
    user_id = user_session_data[SESSION_KEY]
    user_preferences = request.session.get(USERS_PREFERENCES_KEY, {}).get(int(user_id), {})
    request.session.update(user_preferences)

    return HttpResponseRedirect(redirect_to)


@csrf_protect
@never_cache
def logout_current(request, redirect_field_name=REDIRECT_FIELD_NAME):
    redirect_to = request.GET.get(redirect_field_name, settings.LOGIN_REDIRECT_URL)
    
    for idx, u in enumerate(request.session.get(LOGGED_USERS_KEY)):
        if request.user.pk == int(u[SESSION_KEY]):
            break

    user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)

    request.session.get(LOGGED_USERS_KEY).pop(idx)
    request.session.modified = True

    request.user = AnonymousUser()

    return HttpResponseRedirect(redirect_to)

@csrf_protect
@never_cache
def logout(request, user_index, redirect_field_name=REDIRECT_FIELD_NAME):
    """Logout from one specific user profile (except the one logged in currently)"""
    user_index = int(user_index)
    redirect_to = request.GET.get(redirect_field_name, settings.LOGIN_REDIRECT_URL)
    
    if len(request.session.get(LOGGED_USERS_KEY, [])) < (user_index + 1):
        return HttpResponseRedirect(redirect_to)
    
    if int(request.session.get(LOGGED_USERS_KEY)[user_index][SESSION_KEY]) == request.user.pk:
        return HttpResponseRedirect(redirect_to)
    
    request.session.get(LOGGED_USERS_KEY).pop(user_index)
    request.session.modified = True

    return HttpResponseRedirect(redirect_to)


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          extra_context=None, redirect_authenticated_user=False,
          form_valid=_form_valid):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name, request.GET.get(redirect_field_name, settings.LOGIN_REDIRECT_URL))
    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            store_user_preferences(request)
            return form_valid(request, form, redirect_to)
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)