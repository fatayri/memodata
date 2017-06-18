#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, string, csv, codecs, requests, json
from pymystem3 import Mystem
import pandas as pd

m_cache = {}
m = Mystem()
false_subs = set(["с", "в", "к", "г", "д", "е", "ё", "з", "й", "л", "м", "н", "п", "р", "с", "т", "ф", "х", "ц", "ч", "ш", "щ", "ы", "ю", "данна", "ред", "франс", "ст", "главный", "старший",
	"ответ", "мл", "младший", "обл", "з-д", "эл"])
true_subs = set(["управляющий", "заключенный", "учащийся", "учащаяся", "рабочий", "рабочая", "заведующий", "заведующая", "дверевой", "нач-к", "пред",
	"монашка", "ком"])

def get_batch_scores(sentence):
	my_dict, final_sentence = {}, []
	r = requests.get("http://speller.yandex.net/services/spellservice.json/checkText?text=" + sentence)
	true_spelling = r.json()
	if true_spelling == []:
		return sentence
	else:
		for dicti in true_spelling:
			if dicti['s'] != []:
				preliminary_dict = {}
				preliminary_dict[dicti['word']] = dicti['s'][0]
				my_dict.update(preliminary_dict)
	for word in sentence.split(" "):
		if word in my_dict:
			final_sentence.append(my_dict[word])
		elif word.split("-")[0] in my_dict:
			final_sentence.append(my_dict[word.split("-")[0]] + "-" + word.split("-")[1])
		else:
			final_sentence.append(word)
	return " ".join(final_sentence)

def basic_preprocessing(line):
	remove = string.punctuation
	line = line.lower()
	remove = remove.replace(",", "").replace("-", "").replace(":", "")
	pattern = "[{}]".format(remove)
	line = re.sub(pattern, ' ', line)
	line = re.sub("\s+", " ", line)
	line = line.strip()
	line = line.replace("ё", "е")
	return line

def hyphen_lemmatizer(token):
	try:
		lemma = m.lemmatize(token)[0]
		tokens = token.split("-")
		if len(lemma.split("-")) != len(tokens):
			for i, word in enumerate(tokens):
				try:
					word_lemma = m.lemmatize(word)[0]
				except:
					word_lemma = word
				tokens[i] = word_lemma
				final = "-".join(tokens)
		else:
			final = lemma
	except:
		final = ''
	return final

def right_lemmatisation(token):
	if "-" in token:
		new_word = hyphen_lemmatizer(token)
	else:
		try:
			new_word = m.lemmatize(token)[0]
		except:
			new_word = ''
	return new_word

def cashing(w):
	global m_cache
	if w not in m_cache:
		lemma = right_lemmatisation(w)
		pos, list_of_cases, anim = '', '', False
		try:
			pos = m.analyze(w)[0]['analysis'][0]['gr'].split(",")[0]
			list_of_cases = m.analyze(w)[0]['analysis'][0]['gr'].split("=")[1]
			animacy = m.analyze(w)[0]['analysis'][0]['gr'].split(",")[2]
			anim = True if "неод" not in animacy and "од" in animacy and w not in false_subs else False
		except:
			pass
		m_cache[w] = (
			lemma if lemma else '',
			pos,
			list_of_cases,
			anim
		)
	return m_cache[(w)]

def case_based_resolution(profession):
	for word in profession.split(" "):
		if (cashing(word)[1] == "S" and "им,ед" in cashing(word)[2] and word not in false_subs and cashing(word)[3] == True) or word in true_subs:
			return word
		elif (cashing(word)[1] == "S" and "твор" in cashing(word)[2] and word not in false_subs and cashing(word)[0] not in false_subs) or word in true_subs:
			return cashing(word)[0]
	return profession

def animacy_based_resolution(professions):
	dicti = {}
	for potential_profession in professions:
		tokens = potential_profession.split(" ")
		animacies = [cashing(token)[3] for token in tokens]
		if True in animacies:
			dicti[potential_profession] = 1
		else:
			dicti[potential_profession] = 0
	if sum(dicti.values()) == 1:
		return [profession for profession in dicti if dicti[profession] == 1][0]
	elif sum(dicti.values()) > 1:
		return [profession for profession in dicti if dicti[profession] == 1]
	else:
		return "zero"


def women_postprocessing(profession):
	hushing = ["ш", "щ", "ч"]
	if profession[-3:] == "ица":
		new_profession = profession[:-2] + "к"
	elif profession[-5:] == "истка":
		new_profession = profession[:-2]
	elif profession[-2:] == "ая":
		if profession[-3] not in hushing:
			new_profession = profession[:-2] + "ый"
		else:
			new_profession = profession[:-2] + "ий"
	elif profession[-4:] == "аяся":
		if profession[-5] not in hushing:
			new_profession = profession[:-4] + "ыйся"
		else:
			new_profession = profession[:-2] + "ий"
	elif profession[-3:] == "тка":
		new_profession = profession[:-2]
	elif profession[-3:] == "иха":
		new_profession = profession[:-3]
	elif profession[-3:] == "иня":
		new_profession = profession[:-3]
	elif profession[-2:] == "ка":
		new_profession = profession[:-2]
	else:
		new_profession = profession
	return new_profession


def final_profession_resolution(profession):
	final_arr = []
	if "," in profession or ":" in profession:
		if "," in profession:
			professions = profession.split(",")
		elif ":" in profession:
			professions = profession.split(":")
		if animacy_based_resolution(professions) == "zero":
			final_profession = min(professions, key = len)
		elif type(animacy_based_resolution(professions)) == list:
			prs = animacy_based_resolution(professions)
			final_profession = min(prs, key = len)
		else:
			final_profession = animacy_based_resolution(professions)
		final_profession = case_based_resolution(final_profession)
	else:
		final_profession = case_based_resolution(profession)
	final_profession = women_postprocessing(final_profession.strip())
	return final_profession

def professions_detection(line):
	profession = get_batch_scores(line)
	preprocessed_profession = basic_preprocessing(profession)
	final_profession = final_profession_resolution(preprocessed_profession)
	return final_profession

def get_cluster_for_profession(raw_text, df):
	#df=pd.read_csv('final_clusters.csv', header=None)
	profession=professions_detection(raw_text)
	if profession not in df:
		return "not found"
	else:
		return df[profession]

#print(get_cluster_for_profession(professions_detection('зав складом им третьего мая')))
