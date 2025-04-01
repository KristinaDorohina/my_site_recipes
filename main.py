from datetime import datetime
import secrets

from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash


from flask import Flask, render_template, redirect, url_for, flash, request


from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField, FileField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed, FileRequired

# Flask-Uploads для загрузки файлов
from flask_uploads import UploadSet, configure_uploads, IMAGES

# Flask-SQLAlchemy для работы с базой данных
from flask_sqlalchemy import SQLAlchemy

# Flask-Login для аутентификации
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user

app = Flask(__name__)

# Настройка конфигурации приложения
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///my_site.db'

db = SQLAlchemy(app)
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
login_manager = LoginManager(app)  # Flask-Login
login_manager.login_view = 'login'

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


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    dish_types = db.Column(db.String(300))
    photo = db.Column(db.String(300))  # Путь к файлу
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref('recipes', lazy=True))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)  # Дата создания поста
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Связь с пользователем

    # Отношение "многие к одному" с моделью User
    # user = db.relationship('User', backref=db.backref('posts', lazy=True))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        filename = photos.save(form.photo.data)

        # Создание объекта рецепта
        recipe = Recipe(
            title=form.title.data,
            description=form.description.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            dish_types=", ".join(form.dish_types.data),  # Сохраняем выбранные типы блюд
            photo=filename,
            user_id=current_user.id,
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
            flash('Все поля должны быть заполнены', 'danger')
            return redirect(url_for('registration'))

        # Проверяем, что пользователь с таким именем или email уже не существует
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Пользователь с таким именем или email уже существует', 'danger')
            return redirect(url_for('registration'))

        # Хэшируем пароль
        password_hash = generate_password_hash(password)

        user = User(username=username, email=email, password_hash=password_hash)

        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('/login'))
        except Exception as e:
            db.session.rollback()  # Откатываем транзакцию в случае ошибки
            print(f"Ошибка: {e}")
            return 'произошла ошибка'
    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Вчод выполнен успешно!', 'succes')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

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
