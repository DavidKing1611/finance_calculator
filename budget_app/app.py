from flask import Flask, render_template, request, send_file
import pandas as pd
import os
import requests
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)

# Функция для получения курсов валют
def get_exchange_rates(base_currency='RUB'):
    url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"  # URL для API курсов валют
    response = requests.get(url)  # Отправка GET-запроса к API
    if response.status_code == 200:  # Проверка успешности запроса
        return response.json()['rates']  # Возвращаем курсы валют
    else:
        return None  # Если запрос не успешен, возвращаем None

# Функция для конвертации валюты
def convert_currency(amount, from_currency, to_currency, exchange_rates):
    if from_currency == to_currency:  # Если валюты одинаковые, возвращаем исходную сумму
        return amount
    else:
        # Конвертация суммы с учетом курсов валют
        return amount * exchange_rates[to_currency] / exchange_rates[from_currency]

# Функция для сохранения бюджета в CSV файл
def save_budget(income, expenses, filename='budget.csv'):
    data = {'Income': [income], **{category: [amount] for category, amount in expenses.items()}}  # Подготовка данных
    df = pd.DataFrame(data)  # Создание DataFrame
    df.to_csv(get_budget_file_path(filename), index=False)  # Сохранение в CSV файл

# Функция для получения пути к файлу бюджета
def get_budget_file_path(filename='budget.csv'):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)  # Формирование полного пути к файлу

# Функция для загрузки бюджета из CSV файла
def load_budget(filename='budget.csv'):
    file_path = get_budget_file_path(filename)  # Получаем путь к файлу
    if os.path.exists(file_path):  # Проверяем, существует ли файл
        df = pd.read_csv(file_path)  # Загружаем данные из CSV
        if df.empty:  # Если файл пустой
            return 0, {}  # Возвращаем 0 и пустой словарь
        income = df['Income'][0]  # Получаем доход
        expenses = df.drop(columns=['Income']).to_dict(orient='records')[0]  # Получаем расходы
        return income, expenses  # Возвращаем доход и расходы
    else:
        return 0, {}  # Если файл не найден, возвращаем 0 и пустой словарь

# Функция для создания диаграммы расходов
def create_expense_chart(expenses):
    plt.figure(figsize=(4, 2))  # Устанавливаем размер графика
    plt.bar(expenses.keys(), expenses.values(), color='blue')  # Создаем столбчатую диаграмму
    plt.xlabel('Категории расходов')  # Подпись оси X
    plt.ylabel('Сумма')  # Подпись оси Y
    plt.title('Диаграмма расходов')  # Заголовок графика
    plt.xticks(rotation=0)  # Угол наклона меток на оси X

    # Сохраняем диаграмму в буфер
    buf = io.BytesIO()  # Создаем буфер в памяти
    plt.savefig(buf, format='png')  # Сохраняем график в буфер в формате PNG
    plt.close()  # Закрываем график
    buf.seek(0)  # Возвращаем указатель буфера в начало
    return base64.b64encode(buf.getvalue()).decode('utf-8')  # Кодируем содержимое буфера в base64

# Функция для расчета ежемесячного платежа по кредиту
def calculate_monthly_payment(amount, interest_rate, term):
    monthly_interest_rate = interest_rate / 12  # Рассчитываем месячную процентную ставку
    if monthly_interest_rate > 0:
        monthly_payment = amount * monthly_interest_rate * (1 + monthly_interest_rate) ** term / ((1 + monthly_interest_rate) ** term - 1)
    else:
        monthly_payment = amount / term  # Если процентная ставка 0
    return monthly_payment  # Возвращаем ежемесячный платеж


# Главная страница приложения
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':  # Если получен POST-запрос
        try:
            # Получаем данные из формы
            income = float(request.form['income'])  # Доход
            income_currency = request.form['income_currency'].upper()  # Валюта дохода
            expenses = {}  # Словарь для расходов

            # Получаем курсы валют
            exchange_rates = get_exchange_rates(income_currency)

            if not exchange_rates:  # Если курсы не получены
                return render_template('index.html', error="Ошибка получения курсов валют.")

            categories = request.form.getlist('category[]')  # Список категорий расходов
            amounts = request.form.getlist('amount[]')  # Список сумм расходов
            currencies = request.form.getlist('currency[]')  # Список валют расходов

            # Конвертируем каждую категорию расхода в валюту дохода
            for i in range(len(categories)):
                category = categories[i]
                amount = float(amounts[i])
                expense_currency = currencies[i].upper()

                # Конвертируем валюту
                expenses[category] = convert_currency(amount, expense_currency, income_currency, exchange_rates)

            total_expenses = sum(expenses.values())  # Общая сумма расходов
            balance = income - total_expenses  # Остаток
            save_budget(income, expenses)  # Сохраняем бюджет

            # Получаем данные для цели накопления
            goal_amount = float(request.form['goal_amount'])
            goal_currency = request.form['goal_currency'].upper()
            goal_months = int(request.form['goal_months'])

            # Расчет суммы для накопления на цель
            goal_rate = (goal_amount / goal_months) / income  # Процент от дохода для накопления
            monthly_savings = income * goal_rate  # Ежемесячные сбережения

            # Создаем диаграмму расходов
            expense_chart = create_expense_chart(expenses)

            # Возвращаем страницу с итогами бюджета
            return render_template('budget_summary.html', income=income, total_expenses=total_expenses, balance=balance,
                                   expenses=expenses, goal_amount=goal_amount, goal_currency=goal_currency,
                                   goal_months=goal_months, monthly_savings=monthly_savings,
                                   expense_chart=expense_chart)

        except (ValueError, KeyError) as e:  # Обработка ошибок
            return render_template('index.html', error="Пожалуйста, проверьте введенные данные.")

    return render_template('index.html')  # Возвращаем главную страницу

# Страница генерации отчета
@app.route('/generate_report', methods=['GET', 'POST'])
def generate_report():
    if request.method == 'POST':  # Если получен POST-запрос
        start_date = request.form['start_date']  # Начальная дата
        end_date = request.form['end_date']  # Конечная дата
        income, expenses = load_budget()  # Загружаем бюджет

        if expenses is None or not expenses:  # Если нет данных о расходах
            return render_template('generate_report.html', error="Нет данных о расходах.")

        # Создание отчета
        report_data = {
            'Date': [datetime.now().strftime('%Y-%m-%d')],  # Текущая дата
            'Income': [income],  # Доход
            'Total Expenses': [sum(expenses.values())],  # Общие расходы
        }

        for category, amount in expenses.items():  # Добавляем расходы по категориям
            report_data[category] = [amount]

        report_df = pd.DataFrame(report_data)  # Создаем DataFrame для отчета

        # Сохранение отчета в CSV файл
        report_filename = f"financial_report_{start_date}_to_{end_date}.csv"  # Формируем имя файла отчета
        report_df.to_csv(report_filename, index=False)  # Сохраняем отчет в CSV

        return send_file(report_filename, as_attachment=True)  # Отправляем файл пользователю

    return render_template('generate_report.html')  # Возвращаем страницу генерации отчета

# Страница калькулятора кредитов
@app.route('/loan_calculator', methods=['GET', 'POST'])
def loan_calculator():
    monthly_payment = None
    error = None

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])  # Сумма кредита
            interest_rate = float(request.form['interest_rate']) / 100  # Процентная ставка
            term = int(request.form['term'])  # Срок кредита

            # Проверка на нулевой срок или отрицательное значение
            if term <= 0:
                error = "Срок кредита должен быть больше нуля."
            else:
                monthly_payment = calculate_monthly_payment(amount, interest_rate, term)  # Расчет ежемесячного платежа

        except (ValueError, KeyError) as e:  # Обработка ошибок
            error = "Пожалуйста, проверьте введенные данные."

    return render_template('loan_calculator.html', monthly_payment=monthly_payment, error=error)


# Страница экспорта данных
@app.route('/export_data', methods=['GET'])
def export_data():
    income, expenses = load_budget()  # Загружаем бюджет
    if expenses is None or not expenses:  # Если нет данных для экспорта
        return "Нет данных для экспорта.", 400  # Возвращаем ошибку

    # Создание DataFrame для экспорта
    data = {'Income': [income]}  # Словарь с доходом
    data.update(expenses)  # Добавляем расходы
    df = pd.DataFrame(data)  # Создаем DataFrame

    # Сохранение в CSV файл
    filename = 'financial_data.csv'  # Имя файла для экспорта
    df.to_csv(filename, index=False)  # Сохраняем данные в CSV

    return send_file(filename, as_attachment=True)  # Отправляем файл пользователю

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)  # Запускаем Flask приложение в режиме отладки

