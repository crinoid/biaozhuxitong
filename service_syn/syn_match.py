#coding=utf8

from copy import deepcopy

def get_syn_data(path):
    syn_dict={}
    for line in open(path).xreadlines():
        terms=line.strip().split("\t")
        for term in terms:
            new_terms = deepcopy(terms)
            new_terms.remove(term)
            syn_dict[term]=new_terms

    return syn_dict

syn_dict=get_syn_data("merged_syn.csv")

def get_syn_words(term):
    try:
        return syn_dict[term]
    except:
        return []


