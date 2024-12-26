from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///my_site.com'
db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tittle = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)


@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST', 'GET'])
def create():
    if request.method == 'POST':
        print(request.form['title'])
        print(request.form['text'])
    else:
        return render_template('create.html')
    #return render_template('create.html')


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
