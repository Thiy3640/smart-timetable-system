from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("timetable.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            available TEXT,
            free TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            capacity INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            faculty TEXT,
            students INTEGER,
            lectures INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            faculty TEXT,
            room TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def home():

    conn = sqlite3.connect("timetable.db")
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("DELETE FROM faculty")
        cursor.execute("DELETE FROM classrooms")
        cursor.execute("DELETE FROM subjects")
        cursor.execute("DELETE FROM timetable")

        faculty_names = request.form.getlist("faculty_name")
        faculty_available = request.form.getlist("available_slots")
        faculty_free = request.form.getlist("free_slots")

        room_names = request.form.getlist("room_name")
        room_capacity = request.form.getlist("room_capacity")

        subject_names = request.form.getlist("subject_name")
        subject_faculty = request.form.getlist("subject_faculty")
        subject_students = request.form.getlist("subject_students")
        subject_lectures = request.form.getlist("subject_lectures")

        time_slots_raw = request.form.get("time_slots", "")
        time_slots = [s.strip() for s in time_slots_raw.split(",") if s.strip()]

        # STORE DATA
        for i in range(len(faculty_names)):
            if faculty_names[i]:
                cursor.execute(
                    "INSERT INTO faculty (name, available, free) VALUES (?, ?, ?)",
                    (faculty_names[i], faculty_available[i], faculty_free[i])
                )

        for i in range(len(room_names)):
            if room_names[i] and room_capacity[i]:
                cursor.execute(
                    "INSERT INTO classrooms (room, capacity) VALUES (?, ?)",
                    (room_names[i], int(room_capacity[i]))
                )

        for i in range(len(subject_names)):
            if subject_names[i] and subject_students[i] and subject_lectures[i]:
                cursor.execute(
                    "INSERT INTO subjects (name, faculty, students, lectures) VALUES (?, ?, ?, ?)",
                    (subject_names[i],
                     subject_faculty[i],
                     int(subject_students[i]),
                     int(subject_lectures[i]))
                )

        conn.commit()

        # ---------------- SCHEDULING ----------------

        cursor.execute("SELECT name, faculty, students, lectures FROM subjects")
        subjects = cursor.fetchall()

        cursor.execute("SELECT name, available, free FROM faculty")
        faculty_data = cursor.fetchall()

        cursor.execute("SELECT room, capacity FROM classrooms")
        rooms = cursor.fetchall()

        faculty_dict = {}
        for f in faculty_data:
            faculty_dict[f[0]] = {
                "available": [s.strip() for s in f[1].split(",") if s.strip()],
                "free": [s.strip() for s in f[2].split(",") if s.strip()]
            }

        used_faculty = set()
        used_rooms = {}
        subject_day_used = {}
        faculty_day_count = {}
        subject_remaining = {sub[0]: sub[3] for sub in subjects}

        while any(v > 0 for v in subject_remaining.values()):

            progress_made = False

            for sub in subjects:

                sub_name, fac, students, lectures = sub

                if subject_remaining[sub_name] <= 0:
                    continue

                if fac not in faculty_dict:
                    continue

                for slot in time_slots:

                    day, hour = slot.split("-")

                    if sub_name not in subject_day_used:
                        subject_day_used[sub_name] = set()

                    if day in subject_day_used[sub_name]:
                        continue

                    if fac not in faculty_day_count:
                        faculty_day_count[fac] = {}

                    if day not in faculty_day_count[fac]:
                        faculty_day_count[fac][day] = 0

                    if faculty_day_count[fac][day] >= 2:
                        continue

                    if slot not in faculty_dict[fac]["available"]:
                        continue

                    if slot not in faculty_dict[fac]["free"]:
                        continue

                    if (fac, slot) in used_faculty:
                        continue

                    for room, capacity in rooms:
                        if capacity >= students and used_rooms.get(slot) != room:

                            cursor.execute(
                                "INSERT INTO timetable (subject, faculty, room, time) VALUES (?, ?, ?, ?)",
                                (sub_name, fac, room, slot)
                            )

                            used_faculty.add((fac, slot))
                            used_rooms[slot] = room
                            subject_day_used[sub_name].add(day)
                            faculty_day_count[fac][day] += 1
                            subject_remaining[sub_name] -= 1
                            progress_made = True
                            break

                    if subject_remaining[sub_name] <= 0:
                        break

            if not progress_made:
                break

        conn.commit()
        return redirect("/")

    # FETCH DATA FOR DISPLAY

    cursor.execute("SELECT name, available, free FROM faculty")
    faculty_data = cursor.fetchall()

    cursor.execute("SELECT room, capacity FROM classrooms")
    room_data = cursor.fetchall()

    cursor.execute("SELECT name, faculty, students, lectures FROM subjects")
    subject_data = cursor.fetchall()

    cursor.execute("SELECT subject, faculty, room, time FROM timetable")
    timetable_raw = cursor.fetchall()

    grid = {}
    hours = set()

    for subject, faculty, room, time in timetable_raw:
        day, hour = time.split("-")
        hours.add(hour)

        if day not in grid:
            grid[day] = {}

        grid[day][hour] = f"{subject} ({faculty}) - {room}"

    conn.close()

    sorted_hours = sorted(hours, key=lambda x: int(x))

    return render_template("index.html",
                           faculty_data=faculty_data,
                           room_data=room_data,
                           subject_data=subject_data,
                           grid=grid,
                           hours=sorted_hours)


if __name__ == "__main__":
    app.run(debug=True)