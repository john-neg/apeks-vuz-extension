from app.func import *
from app.forms import *
from app.models import User
from werkzeug.utils import redirect
from flask import render_template, request, send_file, url_for, flash
from flask_login import logout_user, login_user, current_user, login_required


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', active='index')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
#
# 3) вместо простых условий можно и нужно использовать
# тернарные операторы вроде value_if_true if condition else value_if_false

@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    form = CalendarForm()
    form.department.choices = list(ApeksData.departments.items())

    if request.method == 'POST':
        if request.form.get('ical_exp') or request.form.get('xlsx_exp'):
            department = request.form.get('department')
            month = request.form.get('month')
            year = request.form.get('year')
            prepod = request.form.get('prepod')

            if request.form.get('ical_exp'):
                filename = lessons_ical_exp(department, prepod, month, year)
            if request.form.get('xlsx_exp'):
                filename = lessons_xlsx_exp(department, prepod, month, year)

            if filename == 'no data':
                form.prepod.choices = list(get_staff(department).items())
                error = f'{staff_name(prepod, department)} - нет занятий в указанный период'
                return render_template('calendar.html', active='calendar',
                                       form=form, department=department, error=error)
            else:
                return redirect(url_for('getfile', filename=filename))
        elif request.form['dept_choose']:    # request.form.get('department'):
            department = request.form.get('department')
            form.prepod.choices = list(get_staff(department).items())
            return render_template('calendar.html', active='calendar', form=form, department=department)

    return render_template('calendar.html', active='calendar', form=form)


@app.route('/<string:filename>', methods=['GET'])  # this is a job for GET, not POST
def getfile(filename):  # check dir name on prod server
    return send_file(app.config['EXPORT_FILE_DIR'] + filename,
                     mimetype='text/plain',
                     attachment_filename=filename,
                     as_attachment=True)


@app.route('/competencies')
@login_required
def competencies():
    return render_template('competencies.html', active='competencies')

@app.route('/competencies_load', methods=['GET', 'POST'])
@login_required
def competencies_load():
    form = CompetenciesLoad()
    form.edu_spec.choices = list(education_specialty().items())
    if request.method == 'POST':
        if request.form['spec_choose']:
            edu_spec = request.form.get('edu_spec')
            # form.edu_spec.choices = list(education_specialty().items())
            form.edu_plans.choices = list(education_plans(edu_spec).items())
            return render_template('competencies_load.html', active='competencies', form=form, edu_spec=edu_spec)
    return render_template('competencies_load.html', active='competencies', form=form)


@app.route('/library')
@login_required
def library():
    return render_template('library.html', active='library')
