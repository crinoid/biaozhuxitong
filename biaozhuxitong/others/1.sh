#!/usr/bin/env bash
#awk -F"\t" '{print $1}' 'service/sug_service/category.csv' > o.csv
cat "service/data/category.csv" | sed s/"部位_非特指"/"部位"/g > o
cat "o1" | sed s/"分期"/"特征词"/g > o
