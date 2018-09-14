# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate  # 权限系统模块
from .models import User

import logging
import json


def index(request):
    return render_to_response("login.html", "")


def check_user_session(request):
    dic = {}
    dic["username"] = request.session.get("username", "")
    return HttpResponse(json.dumps(dic), content_type='json')


def login(request):
    if request.method == 'POST':
        info = request.POST.get("msg", "")
        username, password = info.split(";")
        # 对比提交的数据与数据库中的数据
        user = authenticate(username=username, password=password)
        if user:
            # response = render_to_response('main.html',"")
            # # response = HttpResponse("login")
            # response.set_cookie('username',username,max_age=600) #10分钟expire
            # print request.COOKIES.has_key('username')
            # print request.COOKIES.get("username","")
            request.session["username"] = username
            logger = logging.getLogger('login')
            logger.info("user " + username + " login")
            return HttpResponse(username, content_type="application/text")
        else:
            return HttpResponse("", content_type="application/text")


def log_authority(username):
    return User.objects.get(name=username).log_authority


def new_data_authority(username):
    return User.objects.get(name=username).new_data_authority


def origin_data_authority(username):
    return User.objects.get(name=username).origin_data_authority


def logout(request):
    response = HttpResponse('logout')
    # 清除cookie里保存的username
    if "username" in request:
        response.delete_cookie('username')
        del request.session['username']
    return HttpResponseRedirect("/login/")
