from datetime import datetime
import secrets

from werkzeug.security import generate_password_hash

# Основные импорты Flask
from flask import Flask, render_template, redirect, url_for, flash, request

# Flask-WTF для работы с формами
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField, FileField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed, FileRequired

# Flask-Uploads для загрузки файлов
from flask_uploads import UploadSet, configure_uploads, IMAGES

# Flask-SQLAlchemy для работы с базой данных
from flask_sqlalchemy import SQLAlchemy

# Flask-Login для аутентификации (опционально)
#from flask_login import LoginManager, UserMixin, login_required, current_user

app = Flask(__name__)

# Настройка конфигурации приложения
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///my_site.db'

db = SQLAlchemy(app)
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
#login_manager = LoginManager(app)  # Flask-Login (опционально)

csrf = CSRFProtect(app)


class RecipeForm(FlaskForm):
    title = StringField('Название блюда', validators=[DataRequired()],
                        render_kw={"placeholder": "Введите название блюда с большой буквы, точка в конце не ставится"})
    photo = FileField('Фото готового блюда',
                      validators=[DataRequired(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')],
                      render_kw={"placeholder": "Загрузите одно фото готового блюда"})
    description = TextAreaField('Краткое описание блюда', validators=[DataRequired()],
                                render_kw={"placeholder": "Пара предложений, которые характеризуют ваше блюдо"})
    instructions = TextAreaField('Процесс приготовления', validators=[DataRequired()],
                                 render_kw={"placeholder": "Опишите пошагово процесс приготовления блюда"})
    ingredients = TextAreaField('Ингредиенты', validators=[DataRequired()],
                                render_kw={
                                    "placeholder": "Каждый ингредиент вводите с новой строки и обязательно в таком порядке: название ингредиента - количество"})
    dish_types = SelectMultipleField('Типы блюд', choices=[
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('dinner', 'Ужин'),
        ('dessert', 'Десерт'),
        ('snack', 'Закуска'),
        ('vegetarian', 'Вегетарианское'),
        ('vegan', 'Веганское'),
        ('gluten_free', 'Без глютена')
    ], validators=[DataRequired()])
    submit = SubmitField('Добавить рецепт')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)  # Дата создания поста
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Связь с пользователем

    # Отношение "многие к одному" с моделью User
    # user = db.relationship('User', backref=db.backref('posts', lazy=True))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        filename = photos.save(form.photo.data)

        # Создание объекта рецепта
        recipe = RecipeForm(
            title=form.title.data,
            description=form.description.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            dish_types=", ".join(form.dish_types.data),  # Сохраняем выбранные типы блюд
            photo=filename
        )
        # Сохранение в базу данных
        try:
            db.session.add(recipe)
            db.session.commit()
            flash('Рецепт успешно добавлен!', 'success')
            return redirect(url_for('index'))  # Перенаправление на главную страницу
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при добавлении рецепта.', 'danger')
            print(f"Ошибка: {e}")

    return render_template('add_recipe.html', form=form)


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Проверяем, что все поля заполнены
        if not username or not email or not password:
            return 'Все поля должны быть заполнены'

        # Проверяем, что пользователь с таким именем или email уже не существует
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return 'Пользователь с таким именем или email уже существует'

        # Хэшируем пароль
        password_hash = generate_password_hash(password)

        user = User(username=username, email=email, password_hash=password_hash)

        try:
            db.session.add(user)
            db.session.commit()
            return redirect('/login')
        except Exception as e:
            db.session.rollback()  # Откатываем транзакцию в случае ошибки
            print(f"Ошибка: {e}")
            return 'произошла ошибка'


    else:
        return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@app.route('/account')
def personal_account():
    return render_template('personal_account.html')


@app.route('/create', methods=['POST', 'GET'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']

        post = Post(title=title, text=text)

        try:
            db.session.add(post)
            db.session.commit()
            return redirect('/')
        except:
            return 'Произошла ошибка'
    else:
        return render_template('create.html')


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
