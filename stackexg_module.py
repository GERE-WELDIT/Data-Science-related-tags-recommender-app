import requests as req
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
import networkx as nx
import re
import os, time, math
from gensim.models import Word2Vec

sb.set()

# data folder path
data_filepath = "static/data/tags.csv"


def file_update_time():
    """ returns true if tags file is not updated for more than 2 days"""
    filepath = "static/data/update_time.txt"  # file of interests
    two_days_in_seconds = 172800  # file reupdates in two days

    with open(filepath, "r+") as file:
        modification_time = file.read()
        modified_time = int(modification_time.split()[-1])
    time_difference = time.time() - modified_time

    return time_difference >= two_days_in_seconds


def convert_to_json(json_data):
    """convert json to python list format"""
    list_data = []
    dict_data = json.loads(json_data)
    for item in dict_data["items"]:
        list_data.append([item["tags"]])
    list_data_flatten = [item for item in list_data]
    return list_data_flatten


def get_stackexg_data():
    """get json-format data from stackexg pages"""
    number_of_pages = 120  # how many web pages wants to scrape
    number_of_records = 10000  # number of rows of tags wanted
    tags = []
    for page_number in range(1, number_of_pages + 1):
        data_science_url = "https://api.stackexchange.com/2.2/questions?page={}&pagesize=100&order=desc&sort=activity&site=datascience".format(
            page_number
        )

        if len(tags) == number_of_records:
            break

        req_json_data = req.get(data_science_url)
        # check if stackexg api blocks request from the the ip address
        if not file_update_time():
            break  # break the loop if it is before update  time
        if (
            req_json_data.status_code == 200
        ):  # check request is successful before parsing webpage data
            rows_list_data = convert_to_json(req_json_data.text)
            for row in rows_list_data:
                tags.append(row)
        else:
            print("error due to many requests from this ip address.")

    if len(tags) >= number_of_records:
        # initialize an empty dataframe, write the tags into dataframe.
        df = pd.DataFrame(tags, columns=["tags"])
        # export df to csv file
        df.to_csv("static/data/tags.csv", index=False, header=True)

        # save tags.csv modifications date and time
        filepath = "static/data/update_time.txt"
        with open(filepath, "w+") as file:
            current_time = time.time()
            file.write("timestamp: ")
            file.write(str(round(current_time)))


def load_data(filename):
    """reads the csv file containing tags and returns it into 2d lists of words"""

    # get the tags
    df = pd.read_csv(filename, "r+", delimiter='"', engine="python")
    # add column name
    # get the tags
    df_tags = df["tags"]
    # remove the double-quote via regex
    tags = [(re.sub(r"[^a-zA-Z -]+", "", tag)).split() for tag in df_tags]

    return tags  #  a list of lists


# edges and weights update
def create_edges(list_of_tags):
    """ it create edges between nodes in the same tag(row)"""
    edges = []

    for row in list_of_tags:
        for i in range(0, len(row)):
            for j in range(i + 1, len(row)):
                edges.append((row[i], row[j]))

    return edges


def draw_graph(edges):
    """creates weighted edges of the graph and draw the graph"""
    graph = nx.Graph()
    for edge in edges:
        u, v = edge
        if graph.has_edge(u, v):
            w = graph.get_edge_data(u, v)  # read existed weight of edge from the graph
            updated_weight = (
                w["weight"] + 1
            )  # parse the weight from dictionary , and add 1
            # update edge weight here
            graph.add_edge(u, v, weight=updated_weight)

        else:
            graph.add_edge(u, v, weight=1)
    return graph


def draw_query_graph(G, edges, key_word):
    """returns a subset graph that is associated with node(keyword) a user input queries"""
    g = nx.Graph()  # graph for query
    for edge in edges:
        u, v = edge  # u,v  two nodes form an edge
        w = G.get_edge_data(u, v)  # get weight of each edge
        g.add_edge(u, v, weight=w["weight"])
    pos = nx.spring_layout(g)
    # plt.figure(figsize=(12, 6))
    nx.draw(g, pos, with_labels=True, edge_color="r", width=5)
    weights = nx.get_edge_attributes(g, "weight")
    nx.draw_networkx_edge_labels(g, pos, edge_labels=weights)
    # print("nodes=", g.number_of_nodes(), "edges=", g.number_of_edges())

    # check if same name file exist
    full_image_name = "static/graph_images/" + key_word + ".png"
    images_folder = "static/graph_images/"
    # clear the images folder
    image_files = os.listdir(images_folder)
    for file in image_files:
        os.remove(os.path.join(images_folder, file))
    plt.savefig(
        full_image_name, bbox_inches="tight", transparent=True,
    )
    # plt.show()
    return g


def has_multiple_words(text):  # accepts input from users
    """ check if user entered multiple words and convert them into 1 hypenated words"""
    words = (text.lower()).split()
    key_word = ""
    if len(words) > 1:
        key_word += "-".join(text.split())
    else:
        key_word += text

    return key_word


def bruteforce_main_graph(key_word):

    # read the api codes to get the data from stackexg pages
    get_stackexg_data()  # overwrites into the data file if needs update
    tags = load_data(data_filepath)
    print("number of tags (rows): {} ".format(len(tags)))

    # create list of edges
    edges_list = create_edges(tags)

    G = draw_graph(edges_list)  # [:500]

    # search for query node in the graph:brute-force search
    graph_tags_name = ""
    if G.has_node(key_word):
        query_edges = list(G.edges(key_word))
        g = draw_query_graph(G, query_edges, key_word)
        weights = nx.get_edge_attributes(g, "weight")
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        top_related_tags = 100  # top 100 related tags
        for count, tag in enumerate(sorted_weights):
            u, v = tag[0]
            w = tag[1]
            graph_tags_name += " ({} & {}: {} times) , ".format(u, v, w)
            if count == top_related_tags:
                break

    else:
        graph_tags_name += "Entered node <<{}>> does not exist or probably less commmon term.try other words!".format(
            key_word
        )

    return graph_tags_name


#         **********************Word2Vec tag recommender starts here********************************


def train_word2vec_model(data):
    # creare a model object
    model = Word2Vec(
        data, min_count=5, size=512, window=10, iter=40
    )  # train the model with the data
    return model


def get_word2vec_tags(key_word, top_related_tags=100):
    """returns the most similar tags recommended based on word2vec model"""
    tags = load_data(data_filepath)
    model = train_word2vec_model(tags)  # train the word2vec model
    word2vec_related_tags = ""
    try:
        most_similar_words = model.wv.most_similar(key_word, topn=top_related_tags)
        for word in most_similar_words:
            word2vec_related_tags += "({} & {}: {:.2f}%) , ".format(
                key_word, word[0], word[1] * 100
            )
    except:
        word2vec_related_tags += " word << {} >> is not in word2vec model's training vocabularies.try other words!".format(
            key_word
        )

    return word2vec_related_tags


# if __name__ == "__main__":
#     rel_tags = get_word2vec_tags(key_word)
#     bruteforce_main_graph(key_word)

