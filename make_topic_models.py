from pprint import pprint
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
import os
import numpy as np
import json

###########
# Internal help functions
###########

NR_OF_TOP_WORDS = 25
NR_OF_TOP_DOCUMENTS = 200

# The bow that is used
def get_scikit_bow(documents, ngram_length, vectorizer):
    min_document_frequency = 2
    max_document_frequency = 0.95
    if len(documents) < 3: # if there is only two documents these parameters are the only that work
        min_document_frequency = 1
        max_document_frequency = 1.0
    tf_vectorizer = vectorizer(max_df= max_document_frequency, min_df=min_document_frequency,\
                                   ngram_range = (1, ngram_length), stop_words='english')
    tf = tf_vectorizer.fit_transform(documents)
    inversed = tf_vectorizer.inverse_transform(tf)
    to_return = []
    for el in inversed:
        to_return.append(list(el))
    return to_return, tf_vectorizer, tf

"""
def display_topics(model, feature_names, no_top_words):
    for topic_idx, topic in enumerate(model.components_):
        print ("Topic " +  str(topic_idx))
        print(" ".join([feature_names[i] for i in topic.argsort()[:-no_top_words - 1:-1]]))

# Copied from: https://medium.com/towards-data-science/improving-the-interpretation-of-topic-models-87fd2ee3847d
def display_topics(H, W, feature_names, documents, no_top_words, no_top_documents):
    for topic_idx, topic in enumerate(H):
        print("Topic %d:" % (topic_idx))
        print(" ".join([feature_names[i] for i in topic.argsort()[:-no_top_words - 1:-1]]))
        top_doc_indices = np.argsort( W[:,topic_idx] )[::-1][0:no_top_documents]
        for doc_index in top_doc_indices:
            print(documents[doc_index])
"""


def get_scikit_topics(model, vectorizer, transformed, documents, nr_of_top_words, no_top_documents):

    W = model.transform(transformed)
    H = model.components_

    return_list = []
    feature_names = vectorizer.get_feature_names() 
    for topic_idx, topic in enumerate(H):
        # terms
        term_list = []
        term_set = set()
        for i in topic.argsort()[:-nr_of_top_words - 1:-1]:
            if topic[i] > 0.000:
                term_list.append((feature_names[i], topic[i]))
                for term in feature_names[i].split(" "):
                    term_set.add(term)
        # documents
        doc_list = []
        doc_strength = sorted(W[:,topic_idx])[::-1]
        top_doc_indices = np.argsort( W[:,topic_idx] )[::-1][0:no_top_documents]
        for doc_i, strength in zip(top_doc_indices, doc_strength):
            if strength > 0.000:
                marked_document = documents[doc_i]
                found_term = False
                for term in term_set:
                    if term in documents[doc_i] or term[0].upper() + term[1:] in documents[doc_i] :
                        found_term = True
                        before_changed = marked_document
                        marked_document = marked_document.replace(term, "<b>" + term + "</b>")
                        if  marked_document == before_changed:
                            marked_document = marked_document.replace(term[0].upper() + term[1:], "<b>" + term[0].upper() + term[1:] + "</b>")
                        if marked_document == before_changed:
                            marked_document = marked_document.replace(term.upper(), "<b>" + term.upper() + "</b>")
                if found_term:
                    doc_list.append((doc_i, marked_document, strength)) # only include documents where at least on one of the terms is found
        topic_tuple = (topic_idx, term_list, doc_list)
        return_list.append(topic_tuple)
    return return_list

DOCUMENT = "document"
TOPICS = "topics"
TERMS_IN_TOPIC = "terms_in_topic"
TOPIC_CONFIDENCE = "topic_confidence"
TOPIC_INDEX = "topic_index"

#The strength not normalized. If that is to be done, see for instance:
# https://stackoverflow.com/questions/40597075/python-sklearn-latent-dirichlet-allocation-transform-v-fittransform#40637379
#doc_topic_distr contains the strength for each topic
"""
def get_scikit_topic_for_use(doc_topic_distr, model, tf_vectorizer, documents, no_top_words):
    return_list = []
    feature_names = tf_vectorizer.get_feature_names()
    for document, topic_strength_for_document in zip(documents, doc_topic_distr):        
        return_list_for_document = []
        topic_idx = 0
        for topic, topic_strength in zip(model.components_, topic_strength_for_document):
            term_list = []
            for i in topic.argsort()[:-no_top_words - 1:-1]:
                term_list.append((feature_names[i], topic[i]))
            topic_dict = {TOPIC_INDEX: topic_idx, TERMS_IN_TOPIC : term_list, TOPIC_CONFIDENCE : topic_strength}
            return_list_for_document.append(topic_dict)
            topic_idx = topic_idx + 1
        return_list.append({DOCUMENT: document, TOPICS:return_list_for_document})
    return return_list
"""
#############
# The public functions
#############

############
# Train models
############
# Copied (and modified) from
#https://medium.com/@aneesha/topic-modeling-with-scikit-learn-e80d33668730
def train_scikit_lda_model(documents, number_of_topics, ngram_length):
    texts, tf_vectorizer, tf = get_scikit_bow(documents, ngram_length, CountVectorizer)
    lda = LatentDirichletAllocation(n_components=number_of_topics, max_iter=10, learning_method='online', learning_offset=50.,random_state=0).fit(tf)
    topic_info = get_scikit_topics(lda, tf_vectorizer, tf, documents, NR_OF_TOP_WORDS, NR_OF_TOP_DOCUMENTS)
    return topic_info, lda, tf_vectorizer


# Copied (and modified) from
#https://medium.com/@aneesha/topic-modeling-with-scikit-learn-e80d33668730
def train_scikit_nmf_model(documents, number_of_topics, ngram_length):
    texts, tfidf_vectorizer, tfidf = get_scikit_bow(documents, ngram_length, TfidfVectorizer)
    nmf = NMF(n_components=number_of_topics, random_state=1, alpha=.1, l1_ratio=.5, init='nndsvd').fit(tfidf)
    topic_info = get_scikit_topics(nmf, tfidf_vectorizer, tfidf, documents, NR_OF_TOP_WORDS, NR_OF_TOP_DOCUMENTS)
    return topic_info, nmf, tfidf_vectorizer



def read_test_documents():
    lines = []
    f = open("vaccination-tweets-raw.json")
    text_lines = f.readlines()
    f.close()
    for el in text_lines:
        if '"full_text"' in el:
            cleaned = el.replace('"full_text" : ', "").strip().replace('"', '').replace('\\n*', ' ').replace('\\', ' ').replace('&amp', ' ').replace("'ve", ' have')
            cleande = cleaned.replace("don't", 'do not').replace("doesn't", 'does not').replace("Don't", 'Do not').replace("Doesn't", 'Does not')
            no_links = []
            for word in cleaned.split(" "):
                if "//" not in word and "http" not in word and "@" not in word:
                    no_links.append(word)
            lines.append(" ".join(no_links))
    return list(set(lines))

##########
# Test function
###########


def run_main():
    documents = read_test_documents()

    #documents = ["Human machine interface for lab abc computer applications.",  "A survey of user opinion of computer system response time. System and human system engineering testing of EPS Relation of user perceived response time to error measurement"] *100

    print("Make models for "+ str(len(documents)) + " documents.")
    
    print("*************")
    print("scikit lda")
    topic_info, scikit_lda, tf_vectorizer = train_scikit_lda_model(documents, 10, 2)
    pprint(topic_info)

    print()
    print("*************")
    print("*************")
    print("*************")
    print("scikit nmf")
    topic_info, scikit_nmf, tf_vectorizer = train_scikit_nmf_model(documents, 10, 2)
    pprint(topic_info)

    print("\nMade models for "+ str(len(documents)) + " documents.")
if __name__ == '__main__':
    run_main()
