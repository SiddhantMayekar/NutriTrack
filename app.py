from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from db import MySQL
import config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MYSQL_HOST"] = config.MYSQL_HOST
app.config["MYSQL_PORT"] = config.MYSQL_PORT
app.config["MYSQL_USER"] = config.MYSQL_USER
app.config["MYSQL_PASSWORD"] = config.MYSQL_PASSWORD
app.config["MYSQL_DB"] = config.MYSQL_DB

mysql = MySQL(app)
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check if passwords match
        if password != confirm_password:
            return "Passwords do not match!"

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Connect to MySQL
        cursor = mysql.connection.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        if user:
            cursor.close()
            return "Email already registered!"

        # Insert new user
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, hashed_password)
        )

        mysql.connection.commit()

        cursor.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:

            stored_password = user["password"]

            if check_password_hash(stored_password, password):

                session["user_id"] = user["id"]
                session["full_name"] = user["full_name"]
                session["email"] = user["email"]

                return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!", "success")

    return redirect(url_for("login"))
# Register Page
#@app.route('/register')
#def register():
   # return render_template('register.html')


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    user_id = session["user_id"]

    # ======================================
    # USER DETAILS
    # ======================================
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()

    # ======================================
    # NUTRITION SUMMARY
    # ======================================
    cursor.execute("""
        SELECT
            SUM(calories) AS total_calories,
            SUM(protein) AS total_protein,
            SUM(carbs) AS total_carbs,
            SUM(fats) AS total_fats
        FROM meals
        WHERE user_id=%s
        AND meal_date = CURDATE()
    """, (user_id,))

    nutrition = cursor.fetchone()

    total_calories = nutrition["total_calories"] or 0
    total_protein = nutrition["total_protein"] or 0
    total_carbs = nutrition["total_carbs"] or 0
    total_fats = nutrition["total_fats"] or 0

    # ======================================
    # WATER SUMMARY
    # ======================================
    cursor.execute("""
        SELECT
            SUM(amount) AS total_water
        FROM water_logs
        WHERE user_id=%s
        AND DATE(drink_time)=CURDATE()
    """, (user_id,))

    water = cursor.fetchone()

    total_water = water["total_water"] or 0

    # ======================================
    # BMI
    # ======================================
    height = user["height"] or 0
    weight = user["weight"] or 0

    bmi = 0
    bmi_status = "Not Calculated"

    if height > 0 and weight > 0:

        height_m = height / 100
        bmi = round(weight / (height_m * height_m), 1)

        if bmi < 18.5:
            bmi_status = "Underweight"

        elif bmi < 25:
            bmi_status = "Healthy"

        elif bmi < 30:
            bmi_status = "Overweight"

        else:
            bmi_status = "Obese"

    # ======================================
    # ACTIVITY
    # ======================================
    cursor.execute("""
        SELECT
            SUM(calories) AS total_activity_calories,
            SUM(duration) AS total_duration,
            COUNT(*) AS total_workouts
        FROM activities
        WHERE user_id=%s
        AND activity_date = CURDATE()
    """, (user_id,))

    activity = cursor.fetchone()

    total_activity_calories = activity["total_activity_calories"] or 0
    total_duration = activity["total_duration"] or 0
    total_workouts = activity["total_workouts"] or 0

    steps = total_duration * 100

    workout_status = "Completed" if total_workouts > 0 else "Pending"

    # ======================================
    # PROGRESS
    # ======================================
    calorie_goal = user["calorie_goal"] or 2000
    water_goal = user["water_goal"] or 3000

    nutrition_percent = round((total_calories / calorie_goal) * 100) if calorie_goal else 0
    nutrition_percent = min(nutrition_percent, 100)

    water_percent = round((total_water / water_goal) * 100) if water_goal else 0
    water_percent = min(water_percent, 100)

    remaining_water = max(water_goal - total_water, 0)
    # ======================================
    # TODAY'S MEALS
    # ======================================

    cursor.execute("""
       SELECT meal_type, food_name, calories
       FROM meals
       WHERE user_id=%s
       AND meal_date=CURDATE()
    """, (user_id,))

    meals = cursor.fetchall()

    meal_cards = { 
    "Breakfast": {"food": "Not Added", "calories": 0},
    "Lunch": {"food": "Not Added", "calories": 0},
    "Snacks": {"food": "Not Added", "calories": 0},
    "Dinner": {"food": "Not Added", "calories": 0}
}

    for meal in meals:

       meal_cards[meal["meal_type"]] = {
        "food": meal["food_name"],
        "calories": meal["calories"]
    }
    # ======================================
    # RECENT ACTIVITIES
    # ======================================

    cursor.execute("""
    SELECT
        activity_name,
        duration,
        calories,
        status
    FROM activities
    WHERE user_id=%s
    AND activity_date = CURDATE()
    ORDER BY id DESC
    LIMIT 5
    """, (user_id,))

    recent_activities = cursor.fetchall()

    cursor.close()

    return render_template(

        "dashboard.html",

        user=user,

        total_calories=total_calories,
        total_protein=round(total_protein, 1),
        total_carbs=round(total_carbs, 1),
        total_fats=round(total_fats, 1),

        total_water=total_water,
        remaining_water=remaining_water,

        bmi=bmi,
        bmi_status=bmi_status,

        total_activity_calories=total_activity_calories,
        total_duration=total_duration,
        total_workouts=total_workouts,
        steps=steps,
        workout_status=workout_status,

        nutrition_percent=nutrition_percent,
        water_percent=water_percent,
        meal_cards=meal_cards,
        recent_activities=recent_activities
    )
# Profile
from datetime import date

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # ----------------------------
    # (Your POST update code goes here if you have it)
    # ----------------------------

    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    # ----------------------------
    # Calculate Age
    # ----------------------------

    age = None

    if user["dob"]:

        today = date.today()

        dob = user["dob"]

        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

    cursor.close()

    return render_template(
        "profile.html",
        user=user,
        age=age
    )
@app.route("/update-profile", methods=["POST"])
def update_profile():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE users
        SET
            full_name=%s,
            phone=%s,
            gender=%s,
            dob=%s,
            occupation=%s,
            city=%s,
            country=%s
        WHERE id=%s
    """, (

        request.form["full_name"],
        request.form["phone"],
        request.form["gender"],
        request.form["dob"],
        request.form["occupation"],
        request.form["city"],
        request.form["country"],
        session["user_id"]

    ))

    mysql.connection.commit()

    cursor.close()
    flash("Profile updated successfully!", "success")
    return redirect(url_for("profile"))

@app.route("/update-health", methods=["POST"])
def update_health():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE users
        SET
            height=%s,
            weight=%s,
            goal_weight=%s,
            blood_group=%s,
            activity_level=%s,
            water_goal=%s,
            calorie_goal=%s
        WHERE id=%s
    """, (

        request.form["height"],
        request.form["weight"],
        request.form["goal_weight"],
        request.form["blood_group"],
        request.form["activity_level"],
        request.form["water_goal"],
        request.form["calorie_goal"],
        session["user_id"]

    ))

    mysql.connection.commit()

    cursor.close()
    
    flash("Health information updated successfully!", "success")

    
    return redirect(url_for("profile"))
#Nutrition
@app.route("/nutrition")
def nutrition():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # User information
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )
    user = cursor.fetchone()

    # Today's meals
    cursor.execute("""
        SELECT *
        FROM meals
        WHERE user_id=%s
        AND meal_date = CURDATE()
        ORDER BY meal_time ASC
    """, (session["user_id"],))

    meals = cursor.fetchall()

    breakfast = []
    lunch = []
    dinner = []
    snacks = []

    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fats = 0

    for meal in meals:

        total_calories += meal["calories"] or 0
        total_protein += float(meal["protein"] or 0)
        total_carbs += float(meal["carbs"] or 0)
        total_fats += float(meal["fats"] or 0)

        if meal["meal_type"] == "Breakfast":
            breakfast.append(meal)

        elif meal["meal_type"] == "Lunch":
            lunch.append(meal)

        elif meal["meal_type"] == "Dinner":
            dinner.append(meal)

        else:
            snacks.append(meal)
    # ======================================
    # MEAL HISTORY
    # ======================================

    cursor.execute("""
      SELECT
        meal_date,
        meal_type,
        food_name,
        quantity,
        calories,
        protein,
        carbs,
        fats
    FROM meals
    WHERE user_id=%s
    ORDER BY meal_date DESC, meal_time DESC
    """, (session["user_id"],))

    meal_history = cursor.fetchall()
    cursor.close()

    return render_template(
        "nutrition.html",

        user=user,

        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner,
        snacks=snacks,

        total_calories=total_calories,
        total_protein=round(total_protein, 1),
        total_carbs=round(total_carbs, 1),
        total_fats=round(total_fats, 1),
        meal_history=meal_history
    )
@app.route("/delete_meal/<int:meal_id>", methods=["POST"])
def delete_meal(meal_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        DELETE FROM meals
        WHERE id=%s
        AND user_id=%s
    """, (meal_id, session["user_id"]))

    mysql.connection.commit()

    cursor.close()

    flash("Meal deleted successfully!", "success")

    return redirect(url_for("nutrition"))

@app.route("/add-meal", methods=["POST"])
def add_meal():

    if "user_id" not in session:
        return redirect(url_for("login"))

    meal_type = request.form["meal_type"]
    food_name = request.form["food_name"]
    quantity = request.form["quantity"]

    calories = request.form["calories"] or 0
    protein = request.form["protein"] or 0
    carbs = request.form["carbs"] or 0
    fats = request.form["fats"] or 0

    meal_date = date.today()
    meal_time = datetime.now().strftime("%H:%M:%S")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO meals
        (
            user_id,
            meal_type,
            food_name,
            quantity,
            calories,
            protein,
            carbs,
            fats,
            meal_date,
            meal_time
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    (
        session["user_id"],
        meal_type,
        food_name,
        quantity,
        calories,
        protein,
        carbs,
        fats,
        meal_date,
        meal_time
    ))

    mysql.connection.commit()

    cursor.close()

    flash("Meal added successfully!", "success")

    return redirect(url_for("nutrition"))
#Water
@app.route("/water")
def water():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # User information
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    # Today's water logs
    cursor.execute(
        """
        SELECT *
        FROM water_logs
        WHERE user_id=%s
        AND DATE(drink_time)=CURDATE()
        ORDER BY drink_time DESC
        """,
        (session["user_id"],)
    )

    water_logs = cursor.fetchall()

    # Total water today
    cursor.execute(
        """
        SELECT SUM(amount) AS total_water
        FROM water_logs
        WHERE user_id=%s
        AND DATE(drink_time)=CURDATE()
        """,
        (session["user_id"],)
    )
    result = cursor.fetchone()
    total_water = result["total_water"] or 0
    # ======================================
    # WATER HISTORY
    # ======================================

    cursor.execute("""
    SELECT
        drink_time,
        amount
    FROM water_logs
    WHERE user_id=%s
    ORDER BY drink_time DESC
""", (session["user_id"],))

    water_history = cursor.fetchall()
    cursor.close()
    
    goal = user["water_goal"] or 3000

    progress = round((total_water / goal) * 100)

    remaining = max(goal - total_water, 0)
    print("Total Water:", total_water)
    print("Goal:", goal)
    return render_template(
        "water.html",
        user=user,
        water_logs=water_logs,
        total_water=total_water,
        goal=goal,
        progress=progress,
        remaining=remaining,
        water_history=water_history
    )

@app.route("/add_water", methods=["POST"])
def add_water():

    if "user_id" not in session:
        return redirect(url_for("login"))

    amount = request.form["amount"]

    current_time = datetime.now().strftime("%I:%M %p")
    
    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        INSERT INTO water_logs
        (user_id, amount)
        VALUES (%s,%s)
        """,
        (
            session["user_id"],
            amount
        )
    )

    mysql.connection.commit()

    cursor.close()

    flash("Water added successfully!", "success")

    return redirect(url_for("water"))
#BMI
@app.route("/bmi")
def bmi_calculator():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    cursor.close()

    return render_template("bmi.html", user=user)
#Activity
@app.route("/activity")
def activity():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # Logged in user
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    # Today's activities
    cursor.execute("""
        SELECT *
        FROM activities
        WHERE user_id=%s
        AND activity_date = CURDATE()
        ORDER BY id DESC
    """, (session["user_id"],))

    activities = cursor.fetchall()

    # Total calories burned today
    cursor.execute("""
        SELECT SUM(calories) AS total_calories
        FROM activities
        WHERE user_id=%s
        AND activity_date = CURDATE()
    """, (session["user_id"],))

    result = cursor.fetchone()

    total_calories = result["total_calories"] or 0

    # Total exercise time
    cursor.execute("""
        SELECT SUM(duration) AS total_duration
        FROM activities
        WHERE user_id=%s
        AND activity_date = CURDATE()
    """, (session["user_id"],))

    result = cursor.fetchone()

    total_duration = result["total_duration"] or 0

    # Total completed workouts
    cursor.execute("""
        SELECT COUNT(*) AS completed
        FROM activities
        WHERE user_id=%s
        AND activity_date = CURDATE()
        AND status='Completed'
    """, (session["user_id"],))

    result = cursor.fetchone()

    completed = result["completed"]
    # ======================================
    # ACTIVITY HISTORY
    # ======================================

    cursor.execute("""
    SELECT
        activity_date,
        activity_name,
        duration,
        calories,
        status
    FROM activities
    WHERE user_id=%s
    ORDER BY activity_date DESC, id DESC
""", (session["user_id"],))

    activity_history = cursor.fetchall()
    cursor.close()

    # Estimated Steps
    steps = total_duration * 100

    # Workout Status
    workout_status = "Completed" if completed > 0 else "Pending"

    return render_template(

        "activity.html",

        user=user,

        activities=activities,

        total_calories=total_calories,

        total_duration=total_duration,

        steps=steps,

        workout_status=workout_status,

        activity_history=activity_history

    )
@app.route('/add_activity', methods=['POST'])
def add_activity():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    activity_name = request.form['activity_name']
    duration = request.form['duration']
    calories = request.form['calories']
    activity_date = request.form['activity_date']
    status = request.form['status']

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO activities
        (user_id, activity_name, duration, calories, activity_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
    (
        session['user_id'],
        activity_name,
        duration,
        calories,
        activity_date,
        status
    ))

    mysql.connection.commit()
    cursor.close()

    flash("Activity Added Successfully!", "success")

    return redirect(url_for('activity'))
# Contact
@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
