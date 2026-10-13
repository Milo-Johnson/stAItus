from flask import Flask, request, render_template
from main import apiRequest
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form["question"]
    print(f"Received question: {question}")  # Debugging print statement
    response = apiRequest(question)  
    print(f"Generated answer: {response}")  # Debugging print statement
    
    return render_template("index.html", question=question, answer="hi")

if __name__ == "__main__":
    app.run(debug=True)

   
   
    
    

