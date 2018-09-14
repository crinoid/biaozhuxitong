# coding=utf8
"""biaozhuxitong URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from users import views as users_views
from mainapp import views as mainapp_views
from segment import views as segment_views
from suggest import views as suggest_views
from management import views as management_views
from icd import views as icd_views
from utils import utils

# from service import demo as service_views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # 登录页
    url(r'^login/', users_views.index),
    url(r'^login_check/', users_views.login),
    url(r'^logout/', users_views.logout),

    url(r'^help/', mainapp_views.help),

    url(r'^update_category/', mainapp_views.update_category),
    # 首页
    url(r'^$', mainapp_views.main_page),
    # url(r'^zhenduan/', mainapp_views.main_page),
    # url(r'^shoushu/', mainapp_views.main_page),
    # url(r'^diagnose_page/', mainapp_views.diagnose_page),
    # url(r'^get_authority/', mainapp_views.get_authority),
    url(r'^get_session/', mainapp_views.get_session),
    url(r'^clear_session/', mainapp_views.clearSession),
    # 上传文件
    url(r'^upload/', mainapp_views.upload_file),
    # 跳转至文件查看页
    url(r'^all_files/', mainapp_views.all_files),
    # url(r'^all_files/zhenduan/', mainapp_views.all_files),
    # url(r'^all_files/shoushu/', mainapp_views.all_files),
    # 所有文件
    url(r'^get_files/', management_views.get_files),
    # 选择文件
    url(r'^select_file/', management_views.select_file),
    # 删除文件
    url(r'^delete_file/', management_views.delete_file),
    # 搜索
    url(r'^search_item/', management_views.search_item),
    url(r'^add_segs_sugs/', management_views.add_segs_sugs),
    # 删除分词,标注
    url(r'^delete_segs_sugs/', management_views.delete_segs_sugs),
    # 更新
    url(r'^update_segs_sugs/', management_views.update_segs_sugs),
    # 添加新增的分词,标注至已有词库
    # 下载分词与标注
    # url(r'^download_seg/', management_views.download_seg),
    url(r'^download_sug/', management_views.download_sug),
    # 跳转至新增数据查看页
    url(r'^new_data/', mainapp_views.datafile),
    # url(r'^new_data/zhenduan/', mainapp_views.datafile),
    # url(r'^new_data/shoushu/', mainapp_views.datafile),
    # 查看新添加的数据
    url(r'^get_data/', management_views.get_data),

    url(r'^origin_data/', management_views.origin_data),
    # url(r'^origin_data/zhenduan/', management_views.origin_data),
    # url(r'^origin_data/shoushu/', management_views.origin_data),
    url(r'^get_origin_data/', management_views.get_origin_data),

    url(r'^update_duplicate_data/',management_views.update_duplicate_data),
    url(r'^upload_data_file/', management_views.upload_data_file),

    # 切词
    url(r'^segment/', segment_views.segment),
    url(r'^send_segment/', segment_views.send_segment),
    url(r'^update_seg_source/',segment_views.update_seg_source),
    # 标注
    url(r'^suggest/', suggest_views.suggest),
    url(r'^send_suggest/', suggest_views.send_suggest),
    # 保存标注
    url(r'^save_suggest/', suggest_views.save_suggest),
    # 编辑标注
    url(r'^suggest_edit/', suggest_views.suggest_edit),
    # url(r'^suggest_edit/zhenduan/', suggest_views.suggest_edit),
    # url(r'^suggest_edit/shoushu/', suggest_views.suggest_edit),
    url(r'^get_all_suggests/', suggest_views.get_all_suggests),
    url(r'^add_category/', suggest_views.add_category),
    url(r'^update_sug_category/', suggest_views.update_sug_category),
    url(r'^delete_sug_category/', suggest_views.delete_sug_category),
    # 日志管理
    url(r'^log_management/', management_views.log_management),
    # url(r'^log_management/zhenduan/', management_views.log_management),
    # url(r'^log_management/shoushu/', management_views.log_management),
    url(r'^get_log_info/', management_views.get_log_info),

    # url(r'^update_db/', management_views.update_db),
    url(r'^update_suggests/', suggest_views.update_suggests),

    url(r'^check_session/',users_views.check_user_session),

    #诊断-icd匹配
    url(r'^icd_page/',icd_views.icd_page),
    # url(r'^icd_page/zhenduan/', icd_views.icd_page),
    # url(r'^icd_page/shoushu/', icd_views.icd_page),
    url(r'^load_source/',icd_views.load_source),
    url(r'^upload_diag/',icd_views.upload_diag),
    url(r'^show_diag_file/',icd_views.show_diag_file),
    url(r'^delete_diag_file/', icd_views.delete_diag_file),
    url(r'^submit_icd/',icd_views.submit_icd),
    url(r'^match_icd/', icd_views.match_icd),
    # url(r'^match_icd/zhenduan/', icd_views.match_icd),
    # url(r'^match_icd/shoushu/', icd_views.match_icd),
    url(r'^match_icd_with_code/', icd_views.match_icd_with_code),

    # 智能提示
    url(r'^show_hint/', icd_views.show_hint),
    url(r'^search_from_keyword/',icd_views.search_from_keyword),

]
