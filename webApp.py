from flask import Flask, render_template, request, url_for
import os

IMAGE_FOLDER = os.path.join("static", "graph_images")
# import my module that scrapes the stackoverflow data science web-pages
from stackexg_module import bruteforce_main_graph, has_multiple_words


app = Flask(__name__)  # create instance of flask app
app.config["UPLOAD_FOLDER"] = IMAGE_FOLDER


@app.route("/")
@app.route("/form", methods=["POST", "GET"])
def input_query_form():
    return render_template("form.html")


@app.route("/retrieve_search", methods=["POST"])
def retrieve_search():
    if request.method == "POST":
        entered_word = request.form["text"]
        related_tags = bruteforce_main_graph(entered_word)
        key_word = has_multiple_words(entered_word)
        full_filename = os.path.join(app.config["UPLOAD_FOLDER"], key_word + ".png")

        return render_template(
            "retrieve-search.html",
            related_tags=related_tags,
            graph_image=full_filename,
        )

    else:
        return render_template(
            "retrieve-search.html", message="your have unknown error."
        )


if __name__ == "__main__":
    app.run(debug=True)
