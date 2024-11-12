from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
from .models import User, Car, Service, Order, Task, Report, AppointmentSlot
from . import db, csrf
from .utils import get_current_user, generate_pdf, calculate_statistics

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
@csrf.exempt  # Исключение из CSRF-защиты для входа, если это безопасно
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('main.client_dashboard'))
        else:
            flash("Неверный email или пароль", "error")
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
@csrf.exempt  # Исключение из CSRF-защиты для регистрации
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role')
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, phone=phone, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно", "success")
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/client_dashboard')
def client_dashboard():
    # Проверка, что пользователь авторизован и его роль - 'client'
    if 'role' in session and session['role'] == 'client':
        # Получаем данные клиента
        user = User.query.get(session['user_id'])

        # Получаем заказы клиента
        user_orders = Order.query.filter_by(user_id=session['user_id']).all()

        # Получаем список доступных услуг (если нужно)
        services = Service.query.all()

        return render_template('client/client_dashboard.html', user=user, orders=user_orders, services=services)

    return redirect(url_for('main.index'))  # Перенаправление на главную, если не клиент

@main.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # Проверяем, что пользователь авторизован и его роль - 'client'
    if 'role' in session and session['role'] == 'client':
        user = User.query.get(session['user_id'])  # Получаем данные пользователя

        # Если метод запроса POST (то есть форма отправлена)
        if request.method == 'POST':
            user.name = request.form['name']
            user.email = request.form['email']
            user.phone = request.form['phone']

            db.session.commit()  # Сохраняем изменения в базе данных

            flash("Профиль обновлен!", "success")
            return redirect(url_for('main.client_dashboard'))  # Перенаправляем обратно на панель клиента

        # Если GET - просто отображаем форму с текущими данными
        return render_template('client/edit_profile.html', user=user)

    return redirect(url_for('main.index'))  # Перенаправление на главную, если не клиент

@main.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'role' in session and session['role'] == 'client':
        selected_services = session.get('selected_services')
        if not selected_services:
            return redirect(url_for('main.services'))

        total_duration = sum(Service.query.get(int(service_id)).duration for service_id in selected_services)

        if request.method == 'POST':
            full_name = request.form.get('full_name')
            vin_number = request.form.get('car_vin')
            car_plate = request.form.get('car_plate')
            phone = request.form.get('phone')
            car_year = request.form.get('car_year')
            slot_id = request.form.get('slot_id')

            slot = AppointmentSlot.query.get(slot_id)
            if not slot or not slot.is_available:
                flash("Этот слот недоступен", "error")
                return redirect(url_for('main.appointments'))

            end_time = datetime.combine(slot.appointment_date, slot.start_time) + timedelta(hours=total_duration)
            if end_time.time() > slot.end_time:
                flash("Недостаточно времени для записи на эту услугу", "error")
                return redirect(url_for('main.appointments'))

            slot.is_available = 0
            db.session.commit()

            new_order = Order(user_id=session['user_id'], car_id=1)
            db.session.add(new_order)
            db.session.commit()

            return redirect(url_for('main.generate_order_pdf', order_id=new_order.id))

        today = datetime.now().date()
        available_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_date >= today,
            AppointmentSlot.is_available == 1
        ).all()

        services = [Service.query.get(int(service_id)) for service_id in selected_services]

        return render_template('client/appointments.html', available_slots=available_slots, services=services)

    return redirect(url_for('main.index'))

@main.route('/generate_order_pdf/<int:order_id>')
def generate_order_pdf(order_id):
    order = Order.query.get(order_id)
    if not order:
        return "Заказ не найден", 404

    buffer = generate_pdf(order)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=order_{order_id}.pdf"

    return response

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('selected_services', None)
    return redirect(url_for('main.index'))

@main.route('/tasks')
def tasks():
    if 'role' in session and session['role'] == 'mechanic':
        employee_id = session['user_id']
        tasks = Task.query.filter_by(employee_id=employee_id).all()
        return render_template('employee/mechanic/tasks.html', tasks=tasks)
    return redirect(url_for('main.index'))

@main.route('/reports', methods=['GET', 'POST'])
def reports():
    if 'role' in session and session['role'] == 'mechanic':
        if request.method == 'POST':
            task_id = request.form.get('task_id')
            description = request.form.get('description')
            new_report = Report(task_id=task_id, description=description)
            db.session.add(new_report)
            db.session.commit()
            return redirect(url_for('main.tasks'))
        return render_template('employee/mechanic/reports.html')
    return redirect(url_for('main.index'))

@main.route('/manage_employees', methods=['GET', 'POST'])
def manage_employees():
    if 'role' in session and session['role'] == 'manager':
        if request.method == 'POST':
            name = request.form.get('name')
            role = request.form.get('role')
            email = request.form.get('email')
            password = request.form.get('password')
            hashed_password = generate_password_hash(password)
            new_employee = User(name=name, role=role, email=email, password=hashed_password)
            db.session.add(new_employee)
            db.session.commit()
            return redirect(url_for('main.manage_employees'))
        employees = User.query.filter(User.role.in_(['mechanic', 'manager'])).all()
        return render_template('employee/manager/manage_employees.html', employees=employees)
    return redirect(url_for('main.index'))

@main.route('/manage_services', methods=['GET', 'POST'])
def manage_services():
    if 'role' in session and session['role'] == 'manager':
        if request.method == 'POST':
            service_name = request.form.get('service_name')
            description = request.form.get('description')
            price = request.form.get('price')
            duration = request.form.get('duration')
            new_service = Service(service_name=service_name, description=description, price=price, duration=duration)
            db.session.add(new_service)
            db.session.commit()
            return redirect(url_for('main.manage_services'))
        services = Service.query.all()
        return render_template('employee/manager/manage_services.html', services=services)
    return redirect(url_for('main.index'))

@main.route('/manage_appointments')
def manage_appointments():
    if 'role' in session and session['role'] == 'manager':
        appointments = Order.query.all()
        return render_template('employee/manager/manage_appointments.html', appointments=appointments)
    return redirect(url_for('main.index'))

@main.route('/statistics')
def statistics():
    if 'role' in session and session['role'] == 'manager':
        stats = calculate_statistics()
        return render_template('employee/manager/statistics.html', **stats)
    return redirect(url_for('main.index'))

@main.route('/book_service', methods=['POST'])
def book_service():
    if 'role' in session and session['role'] == 'client':
        service_id = request.form.get('service_id')
        if service_id:
            # Здесь можно добавить логику для создания записи на услугу
            flash("Вы успешно записались на услугу!", "success")
        else:
            flash("Ошибка при записи на услугу.", "error")
        return redirect(url_for('main.client_dashboard'))
    return redirect(url_for('main.index'))

@main.route('/select_services', methods=['GET', 'POST'])
def select_services():
    if 'role' in session and session['role'] == 'client':
        if request.method == 'POST':
            selected_services = request.form.getlist('services')
            session['selected_services'] = selected_services
            return redirect(url_for('main.appointments'))
        services = Service.query.all()
        return render_template('client/select_services.html', services=services)
    return redirect(url_for('main.index'))

@main.route('/appointment_success')
def appointment_success():
    return render_template('client/appointment_success.html')