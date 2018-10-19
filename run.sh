killall -9 uwsgi
killall -9 nginx
#systemctl stop mongod.service
#systemctl start mongod.service
#cd /home/biaozhuxitong/elasticsearch-2.3.3/bin
#./elasticsearch -d -Des.insecure.allow.root=true
cd /home/biaozhuxitong/service
uwsgi -x flask_conf_zd.xml
cd /home/biaozhuxitong/service
uwsgi -x flask_conf_ss.xml
cd /home/biaozhuxitong/service
uwsgi -x flask_conf_zd_sm.xml
cd /home/biaozhuxitong/service_syn
uwsgi -x flask_conf.xml
#cd /home/biaozhuxitong/disease_predict
#uwsgi -x flask_conf.xml
#cd /home/biaozhuxitong/xg1boost
#uwsgi -x flask_conf.xml
cd /home/biaozhuxitong/match_icd/script
uwsgi -x flask_conf.xml
cd /home/biaozhuxitong/biaozhuxitong/uwsgi
uwsgi --ini uwsgi.ini
/usr/local/nginx/sbin/nginx
